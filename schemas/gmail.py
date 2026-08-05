from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ==========================================================
# Email Summary
# ==========================================================

class EmailSummary(BaseModel):
    """
    Lightweight representation of an email.
    Used for inbox listings and search results.
    """

    id: str
    thread_id: str

    subject: str
    sender: str
    sender_email: EmailStr

    snippet: str

    received_at: datetime | None = None

    is_read: bool = False
    is_starred: bool = False


# ==========================================================
# Email Attachment
# ==========================================================

class EmailAttachment(BaseModel):
    """
    Represents an email attachment.
    """

    filename: str

    mime_type: str

    attachment_id: str | None = None

    size: int = 0


# ==========================================================
# Full Email
# ==========================================================

class EmailMessage(BaseModel):
    """
    Complete email representation.
    """

    id: str

    thread_id: str

    subject: str

    sender: str

    sender_email: EmailStr

    recipients: list[EmailStr]

    cc: list[EmailStr] = []

    bcc: list[EmailStr] = []

    body: str

    snippet: str

    received_at: datetime | None = None

    labels: list[str] = []

    attachments: list[EmailAttachment] = []

    is_read: bool = False

    is_starred: bool = False


# ==========================================================
# Inbox Response
# ==========================================================

class InboxResponse(BaseModel):
    """
    Returned when listing emails.
    """

    emails: list[EmailSummary]

    total: int


# ==========================================================
# Send Email
# ==========================================================

class SendEmailRequest(BaseModel):

    to: list[EmailStr]

    cc: list[EmailStr] = []

    bcc: list[EmailStr] = []

    subject: str = Field(..., min_length=1)

    body: str

    html: bool = False


class SendEmailResponse(BaseModel):

    id: str

    thread_id: str

    message: str


# ==========================================================
# Reply
# ==========================================================

class ReplyEmailRequest(BaseModel):

    message_id: str

    body: str

    html: bool = False


# ==========================================================
# Draft
# ==========================================================

class DraftEmailRequest(BaseModel):

    to: list[EmailStr]

    cc: list[EmailStr] = []

    bcc: list[EmailStr] = []

    subject: str

    body: str

    html: bool = False


# ==========================================================
# Search
# ==========================================================

class SearchRequest(BaseModel):

    query: str


# ==========================================================
# Label
# ==========================================================

class Label(BaseModel):

    id: str

    name: str


# ==========================================================
# Thread
# ==========================================================

class Thread(BaseModel):

    id: str

    messages: list[EmailMessage]