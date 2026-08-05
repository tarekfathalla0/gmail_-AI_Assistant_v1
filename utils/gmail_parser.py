from __future__ import annotations

import base64
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from schemas.gmail import EmailMessage, EmailSummary


class GmailParser:
    """
    Converts raw Gmail API responses into our internal schemas.
    """

    @staticmethod
    def parse_summary(message: dict[str, Any]) -> EmailSummary:
        """
        Parse a Gmail message (format=metadata/full) into EmailSummary.
        """

        headers = GmailParser._headers_to_dict(
            message["payload"]["headers"]
        )

        return EmailSummary(
            id=message["id"],
            thread_id=message["threadId"],
            subject=headers.get("Subject", ""),
            sender=GmailParser._extract_sender_name(
                headers.get("From", "")
            ),
            sender_email=GmailParser._extract_sender_email(
                headers.get("From", "")
            ),
            snippet=message.get("snippet", ""),
            received_at=GmailParser._parse_date(
                headers.get("Date")
            ),
            is_read="UNREAD" not in message.get(
                "labelIds",
                [],
            ),
            is_starred="STARRED" in message.get(
                "labelIds",
                [],
            ),
        )

    @staticmethod
    def parse_message(message: dict[str, Any]) -> EmailMessage:
        """
        Parse a complete Gmail message.
        """

        headers = GmailParser._headers_to_dict(
            message["payload"]["headers"]
        )

        body = GmailParser._extract_body(
            message["payload"]
        )

        return EmailMessage(
            id=message["id"],
            thread_id=message["threadId"],
            subject=headers.get("Subject", ""),
            sender=GmailParser._extract_sender_name(
                headers.get("From", "")
            ),
            sender_email=GmailParser._extract_sender_email(
                headers.get("From", "")
            ),
            recipients=GmailParser._split_addresses(
                headers.get("To", "")
            ),
            cc=GmailParser._split_addresses(
                headers.get("Cc", "")
            ),
            body=body,
            snippet=message.get("snippet", ""),
            received_at=GmailParser._parse_date(
                headers.get("Date")
            ),
            labels=message.get("labelIds", []),
            attachments=[],
            is_read="UNREAD" not in message.get(
                "labelIds",
                [],
            ),
            is_starred="STARRED" in message.get(
                "labelIds",
                [],
            ),
        )

    # -------------------------------------------------------
    # Helpers
    # -------------------------------------------------------

    @staticmethod
    def _headers_to_dict(
        headers: list[dict[str, Any]],
    ) -> dict[str, str]:
        return {
            h["name"]: h["value"]
            for h in headers
        }

    @staticmethod
    def _parse_date(
        value: str | None,
    ) -> datetime | None:

        if not value:
            return None

        try:
            return parsedate_to_datetime(value)
        except Exception:
            return None

    @staticmethod
    def _extract_sender_name(
        sender: str,
    ) -> str:

        if "<" in sender:
            return sender.split("<")[0].strip().strip('"')

        return sender

    @staticmethod
    def _extract_sender_email(
        sender: str,
    ) -> str:

        if "<" in sender and ">" in sender:
            return sender.split("<")[1].split(">")[0]

        return sender

    @staticmethod
    def _split_addresses(
        addresses: str,
    ) -> list[str]:

        if not addresses:
            return []

        result = []

        for address in addresses.split(","):

            if "<" in address:
                result.append(
                    address.split("<")[1].split(">")[0]
                )
            else:
                result.append(address.strip())

        return result

    @staticmethod
    def _extract_body(
        payload: dict[str, Any],
    ) -> str:
        """
        Recursively extract the best available body.
        """

        if "parts" in payload:

            for part in payload["parts"]:

                mime = part.get("mimeType")

                if mime == "text/plain":

                    data = (
                        part.get("body", {})
                        .get("data")
                    )

                    if data:
                        return GmailParser._decode(data)

            for part in payload["parts"]:

                body = GmailParser._extract_body(part)

                if body:
                    return body

        data = (
            payload.get("body", {})
            .get("data")
        )

        if data:
            return GmailParser._decode(data)

        return ""

    @staticmethod
    def _decode(data: str) -> str:

        padding = "=" * (-len(data) % 4)

        decoded = base64.urlsafe_b64decode(
            data + padding
        )

        return decoded.decode(
            "utf-8",
            errors="ignore",
        )