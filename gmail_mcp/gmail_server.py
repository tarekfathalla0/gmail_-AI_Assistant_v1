from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gmail_client import gmail_client
from schemas.gmail import (
    EmailMessage,
    InboxResponse,
    SendEmailRequest,
    EmailSummary,
    SendEmailResponse,
    DraftEmailRequest,
)


mcp = FastMCP(
    "gmail"
)


@mcp.tool()
async def list_emails(
    limit: int = 10,
):
    """
    Get latest emails.
    """

    result = await gmail_client.list_messages(
        limit
    )

    return result.model_dump()


@mcp.tool()
async def search_emails(
    query: str,
    limit: int = 10,
):
    """
    Search emails.
    """

    result = await gmail_client.search_messages(
        query,
        limit,
    )

    return result.model_dump()


@mcp.tool()
async def get_email(
    message_id: str,
):
    """
    Get email details.
    """

    result = await gmail_client.get_message(
        message_id
    )

    return result.model_dump()


@mcp.tool()
async def send_email(
    to: str,
    subject: str,
    body: str,
):
    """
    Send an email.

    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body.
    """

    request = SendEmailRequest(
        to=[to],
        subject=subject,
        body=body,
    )

    result = await gmail_client.send_email(
        request
    )

    return result.model_dump()


@mcp.tool()
async def delete_email(
    message_id: str,
):
    """
    Delete email.
    """

    await gmail_client.delete_message(
        message_id
    )

    return {
        "message": "deleted"
    }

@mcp.tool()
async def mark_read(
    message_id: str,
):
    return await gmail_client.mark_read(
        message_id
    )


@mcp.tool()
async def mark_unread(
    message_id: str,
):
    return await gmail_client.mark_unread(
        message_id
    )


@mcp.tool()
async def star_message(
    message_id: str,
):
    return await gmail_client.star_message(
        message_id
    )


@mcp.tool()
async def unstar_message(
    message_id: str,
):
    return await gmail_client.unstar_message(
        message_id
    )


@mcp.tool()
async def archive_message(
    message_id: str,
):
    return await gmail_client.archive_message(
        message_id
    )


@mcp.tool()
async def trash_message(
    message_id: str,
):
    return await gmail_client.trash_message(
        message_id
    )


@mcp.tool()
async def untrash_message(
    message_id: str,
):
    return await gmail_client.untrash_message(
        message_id
    )

@mcp.tool()
async def reply_email(
    message_id: str,
    body: str,
):
    return await gmail_client.reply_email(
        message_id=message_id,
        body=body,
    )

@mcp.tool()
async def create_draft(
    to: list[str],
    subject: str,
    body: str,
):
    request = DraftEmailRequest(
        to=to,
        subject=subject,
        body=body,
    )

    return await gmail_client.create_draft(
        request
    )


@mcp.tool()
async def list_drafts():
    return await gmail_client.list_drafts()


@mcp.tool()
async def send_draft(
    draft_id: str,
):
    return await gmail_client.send_draft(
        draft_id
    )


@mcp.tool()
async def delete_draft(
    draft_id: str,
):
    return await gmail_client.delete_draft(
        draft_id
    )


if __name__ == "__main__":

    mcp.run()