from __future__ import annotations

from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import MemorySaver

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from state import EmailAgentState

from prompts.router import (
    TRIAGE_SYSTEM_PROMPT,
    TRIAGE_USER_PROMPT,
)

from prompts.responder import (
    RESPONDER_SYSTEM_PROMPT,
    RESPONDER_USER_PROMPT,
)

from config import get_settings


settings = get_settings()


llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
)


class TriageResult(BaseModel):
    classification: Literal[
        "ignore",
        "notify",
        "respond",
    ]

    reason: str

    confidence: float = Field(
        ge=0,
        le=1,
    )


triage_llm = llm.with_structured_output(
    TriageResult
)


async def triage_node(
    state: EmailAgentState,
):
    email_content = state.get(
        "email_content",
        "",
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                TRIAGE_SYSTEM_PROMPT,
            ),
            (
                "human",
                TRIAGE_USER_PROMPT,
            ),
        ]
    )

    chain = prompt | triage_llm

    result = await chain.ainvoke(
        {
            "sender": "",
            "subject": "",
            "body": email_content,
        }
    )

    return {
        "classification": result.classification,
        "confidence": result.confidence,
    }


async def ignore_node(
    state: EmailAgentState,
):
    return {
        "response_draft": None,
    }


async def notify_node(
    state: EmailAgentState,
):
    return {
        "response_draft": (
            "Email notification created."
        ),
    }


async def responder_node(
    state: EmailAgentState,
):
    email_content = state.get(
        "email_content",
        "",
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                RESPONDER_SYSTEM_PROMPT,
            ),
            (
                "human",
                RESPONDER_USER_PROMPT,
            ),
        ]
    )

    chain = prompt | llm

    response = await chain.ainvoke(
        {
            "sender": "",
            "subject": "",
            "body": email_content,
            "preferences": "",
        }
    )

    return {
        "response_draft": response.content,
    }


def router(
    state: EmailAgentState,
):
    return state["classification"]


builder = StateGraph(
    EmailAgentState
)


builder.add_node(
    "triage",
    triage_node,
)

builder.add_node(
    "ignore",
    ignore_node,
)

builder.add_node(
    "notify",
    notify_node,
)

builder.add_node(
    "responder",
    responder_node,
)


builder.add_edge(
    START,
    "triage",
)


builder.add_conditional_edges(
    "triage",
    router,
    {
        "ignore": "ignore",
        "notify": "notify",
        "respond": "responder",
    },
)


builder.add_edge(
    "ignore",
    END,
)

builder.add_edge(
    "notify",
    END,
)

builder.add_edge(
    "responder",
    END,
)


memory = MemorySaver()

email_graph = builder.compile(
    checkpointer=memory,
)