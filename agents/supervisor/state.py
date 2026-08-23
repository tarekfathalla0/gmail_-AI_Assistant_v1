from __future__ import annotations

from typing import Literal

from langgraph.graph import MessagesState


class SupervisorState(MessagesState):

    user_id: str = ""
    thread_id: str = ""

    next_agent: Literal[
        "employee",
        "gmail",
        "finish",
    ] | None = None

    employee_info: dict | None = None

    employee_result: dict | None = None

    gmail_result: str | None = None

    rewritten_result: str | None = None

    final_response: str | None = None

    employee_required_for_gmail: bool = False

    step_count: int = 0

    pending_email_approval: bool = False

    skip_gmail_rewrite: bool = False