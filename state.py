from __future__ import annotations

from typing import Annotated, Literal

from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages


class EmailAgentState(MessagesState):
    """
    State used by the email assistant LangGraph.
    """

    email_id: str | None

    classification: Literal[
        "ignore",
        "notify",
        "respond",
    ] | None

    email_content: str | None

    response_draft: str | None

    confidence: float | None

    user_feedback: str | None