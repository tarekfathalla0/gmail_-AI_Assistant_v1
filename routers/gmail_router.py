from fastapi import APIRouter

from gmail_client import gmail_client
from schemas.gmail import (
    EmailMessage,
    InboxResponse,
    SendEmailRequest,
    SendEmailResponse,
)

router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"],
)


@router.get(
    "/messages",
    response_model=InboxResponse,
)
async def list_messages(
    limit: int = 10,
):
    return await gmail_client.list_messages(
        limit=limit
    )


@router.get(
    "/messages/{message_id}",
    response_model=EmailMessage,
)
async def get_message(
    message_id: str,
):
    return await gmail_client.get_message(
        message_id
    )


@router.get(
    "/search",
    response_model=InboxResponse,
)
async def search_messages(
    query: str,
    limit: int = 10,
):
    return await gmail_client.search_messages(
        query=query,
        limit=limit,
    )


@router.post(
    "/send",
    response_model=SendEmailResponse,
)
async def send_email(
    request: SendEmailRequest,
):
    return await gmail_client.send_email(
        request
    )


@router.post(
    "/reply/{message_id}",
    response_model=SendEmailResponse,
)
async def reply_email(
    message_id: str,
    body: str,
    html: bool = False,
):
    return await gmail_client.reply_email(
        message_id=message_id,
        body=body,
        html=html,
    )


@router.delete(
    "/messages/{message_id}",
)
async def delete_message(
    message_id: str,
):
    await gmail_client.delete_message(
        message_id
    )

    return {
        "message": "Email deleted successfully."
    }


@router.post(
    "/messages/{message_id}/archive",
)
async def archive_message(
    message_id: str,
):
    await gmail_client.archive_message(
        message_id
    )

    return {
        "message": "Email archived successfully."
    }


@router.post(
    "/messages/{message_id}/read",
)
async def mark_as_read(
    message_id: str,
):
    await gmail_client.mark_as_read(
        message_id
    )

    return {
        "message": "Email marked as read."
    }


@router.post(
    "/messages/{message_id}/unread",
)
async def mark_as_unread(
    message_id: str,
):
    await gmail_client.mark_as_unread(
        message_id
    )

    return {
        "message": "Email marked as unread."
    }


@router.post(
    "/messages/{message_id}/star",
)
async def star_message(
    message_id: str,
):
    await gmail_client.star_message(
        message_id
    )

    return {
        "message": "Email starred."
    }


@router.post(
    "/messages/{message_id}/unstar",
)
async def unstar_message(
    message_id: str,
):
    await gmail_client.unstar_message(
        message_id
    )

    return {
        "message": "Email unstarred."
    }

@router.post("/send")
async def send_email(
    request: SendEmailRequest,
):
    return await gmail_client.send_email(
        request
    )