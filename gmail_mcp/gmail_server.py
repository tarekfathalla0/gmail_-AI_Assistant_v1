from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gmail_client import gmail_client
from schemas.gmail import (
    SendEmailRequest,
    DraftEmailRequest,
)


mcp = FastMCP("gmail")


# ============================================================
# EMAIL READING
# ============================================================

@mcp.tool()
async def list_emails(
    limit: int = 10,
):
    """
    List the most recent emails in the user's Gmail inbox.

    USE THIS TOOL ONLY when the user asks for the latest/recent
    emails WITHOUT any filtering condition.

    Examples:
    - "show me my last 5 emails"
    - "show latest 10 emails"
    - "what are my newest emails?"

    DO NOT use this tool if the user specifies:
    - sender
    - recipient
    - date
    - month
    - year
    - subject
    - keywords
    - unread/starred
    - attachments
    - any other search/filter condition

    For filtered requests, ALWAYS use search_emails.
    """

    result = await gmail_client.list_messages(
        limit=limit
    )

    return result.model_dump()


@mcp.tool()
async def search_emails(
    query: str,
    limit: int = 10,
):
    """
    Search emails using Gmail search syntax.

    ALWAYS use this tool when the user specifies ANY filtering
    or search condition.

    Examples:

    User:
    "show me emails from LinkedIn"

    Use:
    query="from:linkedin"

    --------------------------------------------------

    User:
    "show me emails in July"

    Use:
    query="after:2026/07/01 before:2026/08/01"

    --------------------------------------------------

    User:
    "show me emails from LinkedIn in July"

    Use:
    query="from:linkedin after:2026/07/01 before:2026/08/01"

    --------------------------------------------------

    User:
    "show emails about interviews"

    Use:
    query="interview"

    --------------------------------------------------

    User:
    "show unread emails"

    Use:
    query="is:unread"

    --------------------------------------------------

    User:
    "show starred emails"

    Use:
    query="is:starred"

    The query must be a valid Gmail search query.

    IMPORTANT:
    Do NOT use list_emails when the user provides a filter.
    """

    result = await gmail_client.search_messages(
        query=query,
        limit=limit,
    )

    return result.model_dump()


@mcp.tool()
async def get_email(
    message_id: str,
):
    """
    Get the full details of a specific email.

    Use this when the user asks to open, read, or inspect
    a specific email identified by its message ID.
    """

    result = await gmail_client.get_message(
        message_id
    )

    return result.model_dump()


# ============================================================
# SEND EMAIL
# ============================================================

@mcp.tool()
async def send_email(
    to: str,
    subject: str,
    body: str,
):
    """
    Send an email to a recipient.
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


# ============================================================
# EMAIL MANAGEMENT
# ============================================================

@mcp.tool()
async def delete_email(
    message_id: str,
):
    """
    Permanently delete an email.
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
    """
    Mark an email as read.
    """

    return await gmail_client.mark_read(
        message_id
    )


@mcp.tool()
async def mark_unread(
    message_id: str,
):
    """
    Mark an email as unread.
    """

    return await gmail_client.mark_unread(
        message_id
    )


@mcp.tool()
async def star_message(
    message_id: str,
):
    """
    Star an email.
    """

    return await gmail_client.star_message(
        message_id
    )


@mcp.tool()
async def unstar_message(
    message_id: str,
):
    """
    Remove the star from an email.
    """

    return await gmail_client.unstar_message(
        message_id
    )


@mcp.tool()
async def archive_message(
    message_id: str,
):
    """
    Archive an email.
    """

    return await gmail_client.archive_message(
        message_id
    )


@mcp.tool()
async def trash_message(
    message_id: str,
):
    """
    Move an email to trash.
    """

    return await gmail_client.trash_message(
        message_id
    )


@mcp.tool()
async def untrash_message(
    message_id: str,
):
    """
    Restore an email from trash.
    """

    return await gmail_client.untrash_message(
        message_id
    )


# ============================================================
# REPLY
# ============================================================

@mcp.tool()
async def reply_email(
    message_id: str,
    body: str,
):
    """
    Reply to an existing email.
    """

    return await gmail_client.reply_email(
        message_id=message_id,
        body=body,
    )


# ============================================================
# DRAFTS
# ============================================================

@mcp.tool()
async def create_draft(
    to: list[str],
    subject: str,
    body: str,
):
    """
    Create a Gmail draft.
    """

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
    """
    List Gmail drafts.
    """

    return await gmail_client.list_drafts()


@mcp.tool()
async def send_draft(
    draft_id: str,
):
    """
    Send an existing Gmail draft.
    """

    return await gmail_client.send_draft(
        draft_id
    )


@mcp.tool()
async def delete_draft(
    draft_id: str,
):
    """
    Delete a Gmail draft.
    """

    return await gmail_client.delete_draft(
        draft_id
    )


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":
    mcp.run()