from __future__ import annotations
from email.utils import parsedate_to_datetime
import asyncio
import base64

import httpx

from auth import oauth
from token_manager import token_manager
from schemas.gmail import (
    EmailMessage,
    InboxResponse,
    SendEmailRequest,
    EmailSummary,
    SendEmailResponse,
    DraftEmailRequest,
)
from email.mime.text import MIMEText


class GmailClient:
    """
    Client for Gmail API.
    """

    def __init__(self):
        self.base_url = (
            "https://gmail.googleapis.com/gmail/v1"
        )


    async def _headers(self):

        access_token = (
            await oauth.get_valid_access_token()
        )

        if not access_token:
            raise Exception(
                "Gmail authentication required."
            )

        return {
            "Authorization": (
                f"Bearer {access_token}"
            ),
            "Content-Type": "application/json",
        }


    async def list_messages(
    self,
    limit: int = 10,
) -> InboxResponse:

        headers = await self._headers()

        url = (
            f"{self.base_url}"
            "/users/me/messages"
        )

        async with httpx.AsyncClient() as client:

            response = await client.get(
                url,
                headers=headers,
                params={
                    "maxResults": limit
                },
            )

        response.raise_for_status()

        data = response.json()

        message_ids = [
            message["id"]
            for message in data.get("messages", [])
        ]

        messages = await asyncio.gather(
            *(
                self.get_message(message_id)
                for message_id in message_ids
            )
        )

        emails = [
            EmailSummary(
                id=email.id,
                thread_id=email.thread_id,
                subject=email.subject,
                sender=email.sender,
                sender_email=email.sender_email,
                snippet=email.snippet,
                received_at=email.received_at,
                is_read="UNREAD" not in email.labels,
                is_starred="STARRED" in email.labels,
            )
            for email in messages
        ]

        return InboxResponse(
            emails=emails,
            total=len(emails)
        )

    async def get_message(
    self,
    message_id: str,
) -> EmailMessage:

        headers = await self._headers()

        url = (
            f"{self.base_url}"
            f"/users/me/messages/{message_id}"
        )

        async with httpx.AsyncClient() as client:

            response = await client.get(
                url,
                headers=headers,
                params={
                    "format": "full"
                },
            )

        response.raise_for_status()

        data = response.json()

        payload = data.get(
            "payload",
            {}
        )

        email_headers = payload.get(
            "headers",
            []
        )


        header_map = {
            h["name"].lower(): h["value"]
            for h in email_headers
        }


        sender_raw = header_map.get(
            "from",
            ""
        )

        subject = header_map.get(
            "subject",
            ""
        )

        date_raw = header_map.get(
            "date"
        )


        sender_email = (
            sender_raw
            .split("<")[-1]
            .replace(">", "")
            .strip()
        )


        received_at = None

        if date_raw:
            try:
                received_at = parsedate_to_datetime(
                    date_raw
                )
            except Exception:
                pass


        snippet = data.get(
            "snippet",
            ""
        )


        return EmailMessage(
            id=data["id"],
            thread_id=data.get(
                "threadId",
                ""
            ),
            subject=subject,
            sender=sender_raw,
            sender_email=sender_email,
            recipients=[],
            body="",
            snippet=snippet,
            received_at=received_at,
            labels=data.get(
                "labelIds",
                []
            ),
        )

    async def send_email(
    self,
    request: SendEmailRequest,
) -> SendEmailResponse:

        headers = await self._headers()

        if request.html:
            message = MIMEText(
                request.body,
                "html",
            )
        else:
            message = MIMEText(
                request.body,
                "plain",
            )

        message["To"] = ", ".join(request.to)

        if request.cc:
            message["Cc"] = ", ".join(request.cc)

        if request.bcc:
            message["Bcc"] = ", ".join(request.bcc)

        message["Subject"] = request.subject

        raw = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()

        payload = {
            "raw": raw
        }

        async with httpx.AsyncClient() as client:

            response = await client.post(
                f"{self.base_url}/users/me/messages/send",
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        data = response.json()

        return SendEmailResponse(
            id=data["id"],
            thread_id=data["threadId"],
            message="Email sent successfully.",
        )


    async def search_messages(
        self,
        query: str,
        limit: int = 10,
    ) -> InboxResponse:

        headers = await self._headers()

        url = (
            f"{self.base_url}"
            "/users/me/messages"
        )

        params = {
            "q": query,
            "maxResults": limit,
        }

        async with httpx.AsyncClient() as client:

            response = await client.get(
                url,
                headers=headers,
                params=params,
            )

        response.raise_for_status()

        data = response.json()

        return InboxResponse(
            emails=data.get(
                "messages",
                []
            ),
            total=len(
                data.get(
                    "messages",
                    []
                )
            )
        )


    async def delete_message(
        self,
        message_id: str,
    ):

        headers = await self._headers()

        url = (
            f"{self.base_url}"
            f"/users/me/messages/{message_id}"
        )

        async with httpx.AsyncClient() as client:

            response = await client.delete(
                url,
                headers=headers,
            )

        response.raise_for_status()

    async def modify_labels(
    self,
    message_id: str,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
):
        headers = await self._headers()

        url = (
            f"{self.base_url}"
            f"/users/me/messages/{message_id}/modify"
        )

        payload = {
            "addLabelIds": add_labels or [],
            "removeLabelIds": remove_labels or [],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        return response.json()


    async def mark_read(
        self,
        message_id: str,
    ):
        return await self.modify_labels(
            message_id=message_id,
            remove_labels=["UNREAD"],
        )


    async def mark_unread(
        self,
        message_id: str,
    ):
        return await self.modify_labels(
            message_id=message_id,
            add_labels=["UNREAD"],
        )


    async def star_message(
        self,
        message_id: str,
    ):
        return await self.modify_labels(
            message_id=message_id,
            add_labels=["STARRED"],
        )


    async def unstar_message(
        self,
        message_id: str,
    ):
        return await self.modify_labels(
            message_id=message_id,
            remove_labels=["STARRED"],
        )


    async def archive_message(
        self,
        message_id: str,
    ):
        return await self.modify_labels(
            message_id=message_id,
            remove_labels=["INBOX"],
        )


    async def trash_message(
        self,
        message_id: str,
    ):
        headers = await self._headers()

        url = (
            f"{self.base_url}"
            f"/users/me/messages/{message_id}/trash"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
            )

        response.raise_for_status()

        return response.json()


    async def untrash_message(
        self,
        message_id: str,
    ):
        headers = await self._headers()

        url = (
            f"{self.base_url}"
            f"/users/me/messages/{message_id}/untrash"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
            )

        response.raise_for_status()

        return response.json()

    async def reply_email(
    self,
    message_id: str,
    body: str,
):
        headers = await self._headers()

        # Get the original Gmail message
        url = (
            f"{self.base_url}"
            f"/users/me/messages/{message_id}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params={
                    "format": "full",
                },
            )

        response.raise_for_status()

        raw = response.json()

        headers_list = raw["payload"]["headers"]

        subject = ""
        from_email = ""

        for header in headers_list:

            if header["name"].lower() == "subject":
                subject = header["value"]

            elif header["name"].lower() == "from":
                from_email = header["value"]

        if not subject.startswith("Re:"):
            subject = f"Re: {subject}"

        message = MIMEText(body)

        message["To"] = from_email
        message["Subject"] = subject
        message["In-Reply-To"] = raw["id"]
        message["References"] = raw["id"]

        encoded = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()

        payload = {
            "raw": encoded,
            "threadId": raw["threadId"],
        }

        url = (
            f"{self.base_url}"
            "/users/me/messages/send"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        return {
            "message": "Reply sent successfully.",
            **response.json(),
        }

    async def create_draft(
    self,
    request: DraftEmailRequest,
):
        headers = await self._headers()

        message = MIMEText(request.body)

        message["To"] = ",".join(request.to)
        message["Subject"] = request.subject

        if request.cc:
            message["Cc"] = ",".join(request.cc)

        if request.bcc:
            message["Bcc"] = ",".join(request.bcc)

        encoded = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()

        payload = {
            "message": {
                "raw": encoded
            }
        }

        url = (
            f"{self.base_url}"
            "/users/me/drafts"
        )

        async with httpx.AsyncClient() as client:

            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        return response.json()

    async def list_drafts(
    self,
):
        headers = await self._headers()

        url = (
            f"{self.base_url}"
            "/users/me/drafts"
        )

        async with httpx.AsyncClient() as client:

            response = await client.get(
                url,
                headers=headers,
            )

        response.raise_for_status()

        return response.json()

    async def delete_draft(
    self,
    draft_id: str,
):
        headers = await self._headers()

        url = (
            f"{self.base_url}"
            f"/users/me/drafts/{draft_id}"
        )

        async with httpx.AsyncClient() as client:

            response = await client.delete(
                url,
                headers=headers,
            )

        response.raise_for_status()

        return {
            "message": "Draft deleted."
        }

    async def send_draft(
    self,
    draft_id: str,
):
        headers = await self._headers()

        url = (
            f"{self.base_url}"
            "/users/me/drafts/send"
        )

        payload = {
            "id": draft_id
        }

        async with httpx.AsyncClient() as client:

            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        return response.json()


gmail_client = GmailClient()