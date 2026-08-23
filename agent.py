from __future__ import annotations

import asyncio
import logging
import time

from langchain_groq import ChatGroq
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt

from types import SimpleNamespace
from typing import Any

from config import get_settings
from data.memory_service import memory_service
from langgraph.checkpoint.memory import InMemorySaver
from mcp_client import get_mcp_tools


logger = logging.getLogger(__name__)

settings = get_settings()


# ============================================================
# LLM
# ============================================================

llm = ChatGroq(
    model=settings.GROQ_MODEL_NAME,
    api_key=settings.GROQ_API_KEY,
    temperature=0,
)


# ============================================================
# CHECKPOINT
# ============================================================

checkpoint = InMemorySaver()


# ============================================================
# CACHED TOOLS
# ============================================================

_cached_email_tools: list[Any] | None = None

_approval_agent = None


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an intelligent Gmail AI assistant.

You have access to Gmail tools.

Your job is to perform Gmail operations requested by the user.

==================================================
MEMORY
==================================================

You may receive long-term user context.

Use relevant memory silently.

Never say:

- "I cannot remember"
- "I don't have memory"
- "I cannot store information"

Do not explain the memory system.

Treat provided memory as trusted context.

==================================================
GMAIL TOOL SELECTION
==================================================

Use the correct Gmail tool for the user's request.

IMPORTANT:

If the user asks for:

"latest emails"
"last 5 emails"
"recent emails"

use:

list_emails

If the user asks for emails from a person, sender, company, subject,
keyword, date, month, year, etc., use:

search_emails

Examples:

"show me emails from LinkedIn"

Use:

search_emails

with an appropriate Gmail search query such as:

from:linkedin

or:

from:(linkedin)

depending on the request.

Example:

"show me emails from July"

Use:

search_emails

with an appropriate Gmail date query.

Do NOT use list_emails when the user has specified a search condition.

Do NOT invent Gmail search queries when the user's request is ambiguous.

==================================================
EMAIL SENDING
==================================================

When sending an email:

- Use a clear subject.
- Use the user's language unless another language is requested.
- Write a professional greeting.
- State the purpose clearly.
- Include the requested action.
- Use short paragraphs.
- End with a professional closing.
- Never invent names.
- Never invent dates.
- Never invent contact details.
- Never invent a signature.

IMPORTANT:

Never send an email directly.

The send_email tool has human approval built into it.

==================================================
EMPLOYEE INFORMATION
==================================================

If employee information is provided in context, use the employee email
when the user refers to the employee using phrases such as:

- له
- لها
- هو
- هي
- ابعتله
- ابعتلها
- الشخص ده
- الموظف ده
- that person
- that employee

Do not ask for the employee email if it is already available.

==================================================
OUTPUT
==================================================

After completing a Gmail operation, give the user a concise useful response.

Do not repeat unnecessary information.

Do not claim an email was sent unless the Gmail send tool actually succeeded.
"""


# ============================================================
# APPROVAL HELPERS
# ============================================================

def _approval_response(
    to: str,
    subject: str,
    body: str,
) -> str:

    return (
        "Email ready for approval:\n\n"
        f"To: {to}\n"
        f"Subject: {subject}\n\n"
        f"Body:\n{body}\n\n"
        "Reply with:\n"
        "- approve → send the email\n"
        "- cancel → discard the email\n"
        "- edit: <new body> → modify the email"
    )


def _approval_decision(
    value,
) -> tuple[str, str | None]:

    if isinstance(value, dict):

        action = str(
            value.get("action", "")
        ).lower().strip()

        body = value.get("body")

        return action, body

    text = str(value).strip()

    lower = text.lower()

    if lower in {
        "approve",
        "approved",
        "yes",
        "send",
        "ok",
    }:
        return "approve", None

    if lower in {
        "cancel",
        "cancelled",
        "canceled",
        "no",
        "discard",
    }:
        return "cancel", None

    if lower.startswith("edit:"):

        return (
            "edit",
            text[5:].strip(),
        )

    # Treat unknown input as edit.
    return "edit", text


# ============================================================
# APPROVAL-WRAPPED SEND TOOL
# ============================================================

def _email_tools(tools):

    send_tool = next(
        (
            tool
            for tool in tools
            if tool.name == "send_email"
        ),
        None,
    )

    if send_tool is None:

        raise RuntimeError(
            "send_email MCP tool was not found."
        )

    async def send_email_with_approval(
        to: str,
        subject: str,
        body: str,
    ):

        # ----------------------------------------------------
        # FIRST APPROVAL
        # ----------------------------------------------------

        approval = interrupt(
            {
                "type": "email_approval",
                "to": to,
                "subject": subject,
                "body": body,
            }
        )

        action, edited_body = _approval_decision(
            approval
        )

        # ----------------------------------------------------
        # CANCEL
        # ----------------------------------------------------

        if action == "cancel":

            return "Email cancelled."

        # ----------------------------------------------------
        # EDIT
        # ----------------------------------------------------

        if action == "edit":

            body = (
                edited_body
                or body
            )

            # Ask for approval again.
            approval = interrupt(
                {
                    "type": "email_approval",
                    "to": to,
                    "subject": subject,
                    "body": body,
                }
            )

            action, edited_body = _approval_decision(
                approval
            )

            if action == "cancel":

                return "Email cancelled."

            if action == "edit":

                return (
                    "Email still needs approval. "
                    "Please approve the displayed email."
                )

        # ----------------------------------------------------
        # SEND ONLY AFTER APPROVAL
        # ----------------------------------------------------

        if action == "approve":

            result = await send_tool.ainvoke(
                {
                    "to": to,
                    "subject": subject,
                    "body": body,
                }
            )

            return result

        return "Email cancelled."

    approval_tool = StructuredTool.from_function(
        coroutine=send_email_with_approval,
        name="send_email",
        description=(
            "Prepare an email and require explicit human approval "
            "before sending it. Never send without approval."
        ),
        args_schema=send_tool.args_schema,
    )

    return [
        (
            approval_tool
            if tool.name == "send_email"
            else tool
        )
        for tool in tools
    ]


# ============================================================
# BUILD AGENT
# ============================================================

async def _build_email_agent(
    prompt: str = SYSTEM_PROMPT,
):

    global _cached_email_tools

    if _cached_email_tools is None:

        raw_tools = await get_mcp_tools()

        _cached_email_tools = _email_tools(
            raw_tools
        )

    return create_react_agent(
        model=llm,
        tools=_cached_email_tools,
        prompt=prompt,
        checkpointer=checkpoint,
    )


# ============================================================
# PENDING APPROVAL
# ============================================================

async def has_pending_email_approval(
    thread_id: str,
) -> bool:

    global _approval_agent

    if _approval_agent is None:

        _approval_agent = await _build_email_agent()

    snapshot = await _approval_agent.aget_state(
        {
            "configurable": {
                "thread_id": thread_id,
            }
        }
    )

    return any(
        task.interrupts
        for task in getattr(
            snapshot,
            "tasks",
            (),
        )
    )


# ============================================================
# MEMORY LOGGING
# ============================================================

async def _remember_and_log(
    *,
    user_id: str,
    user_message: str,
    assistant_message: str,
) -> None:

    try:

        await memory_service.remember(
            user_id=user_id,
            user_message=user_message,
            assistant_message=assistant_message,
        )

    except Exception:

        # Memory failure must not break Gmail.
        logger.exception(
            "Background memory persistence failed"
        )


# ============================================================
# MAIN AGENT
# ============================================================

async def run_email_agent(
    message: str,
    thread_id: str = "default",
    user_id: str = "default",
    pending_approval: bool | None = None,
):

    started_at = time.perf_counter()

    # ========================================================
    # FORGET COMMANDS
    # ========================================================

    text = message.strip()
    lower = text.lower()

    if lower.startswith("forget "):

        query = text[7:].strip()

        deleted = await memory_service.forget(
            user_id=user_id,
            query=query,
        )

        if deleted == -1:

            return {
                "messages": [
                    SimpleNamespace(
                        content=(
                            "I found many possible matches "
                            "for that phrase. Please be more specific."
                        )
                    )
                ]
            }

        if deleted == -2:

            return {
                "messages": [
                    SimpleNamespace(
                        content=(
                            f"No exact matches found for: {query}"
                        )
                    )
                ]
            }

        return {
            "messages": [
                SimpleNamespace(
                    content=(
                        f"Okay — deleted {deleted} "
                        f"matching memory(ies) for: {query}"
                    )
                )
            ]
        }

    if lower in {
        "forget it",
        "forget that",
    }:

        return {
            "messages": [
                SimpleNamespace(
                    content=(
                        "Please tell me what you'd like me "
                        "to forget."
                    )
                )
            ]
        }

    # ========================================================
    # MEMORY RETRIEVAL
    # ========================================================

    stage_started_at = time.perf_counter()

    try:

        memory_context = await memory_service.retrieve(
            user_id=user_id,
            query=message,
        )

    except Exception:

        logger.exception(
            "Memory retrieval failed"
        )

        memory_context = None

    logger.info(
        "latency operation=email_memory_retrieve "
        "latency_ms=%.2f status=success",
        (
            time.perf_counter()
            - stage_started_at
        ) * 1000,
    )

    print(
        "========== MEMORY CONTEXT =========="
    )

    print(memory_context)

    print(
        "===================================="
    )

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    prompt = SYSTEM_PROMPT

    if memory_context:

        prompt += f"""

IMPORTANT USER CONTEXT:

{memory_context}

Use this context only when relevant.
Do not mention the memory system.
"""

    # ========================================================
    # BUILD AGENT
    # ========================================================

    stage_started_at = time.perf_counter()

    try:

        agent = await _build_email_agent(
            prompt
        )

    except Exception:

        logger.exception(
            "Email agent build failed"
        )

        raise

    logger.info(
        "latency operation=email_agent_build "
        "latency_ms=%.2f status=success",
        (
            time.perf_counter()
            - stage_started_at
        ) * 1000,
    )

    # ========================================================
    # CONFIG
    # ========================================================

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    # ========================================================
    # CHECK APPROVAL STATE
    # ========================================================

    if pending_approval is None:

        snapshot = await agent.aget_state(
            config
        )

        pending_approval = any(
            task.interrupts
            for task in getattr(
                snapshot,
                "tasks",
                (),
            )
        )

    # ========================================================
    # INPUT
    # ========================================================

    if pending_approval:

        invoke_input = Command(
            resume=message
        )

    else:

        invoke_input = {
            "messages": [
                (
                    "user",
                    message,
                )
            ]
        }

    # ========================================================
    # RUN AGENT
    # ========================================================

    stage_started_at = time.perf_counter()

    try:

        result = await agent.ainvoke(
            invoke_input,
            config=config,
        )

    except Exception:

        logger.exception(
            "Email agent invocation failed"
        )

        raise

    logger.info(
        "latency operation=email_agent_invoke "
        "latency_ms=%.2f status=success",
        (
            time.perf_counter()
            - stage_started_at
        ) * 1000,
    )

    # ========================================================
    # HANDLE INTERRUPT
    # ========================================================

    interrupts = result.get(
        "__interrupt__",
        (),
    )

    if interrupts:

        request = interrupts[0].value

        return {
            "messages": [
                SimpleNamespace(
                    content=_approval_response(
                        request["to"],
                        request["subject"],
                        request["body"],
                    )
                )
            ]
        }

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    messages = result.get(
        "messages",
        [],
    )

    if not messages:

        assistant_message = (
            "The Gmail operation completed."
        )

    else:

        assistant_message = (
            messages[-1].content
        )

    # ========================================================
    # BACKGROUND MEMORY
    # ========================================================

    asyncio.create_task(
        _remember_and_log(
            user_id=user_id,
            user_message=message,
            assistant_message=assistant_message,
        )
    )

    logger.info(
        "latency operation=email_agent_total "
        "latency_ms=%.2f status=success",
        (
            time.perf_counter()
            - started_at
        ) * 1000,
    )

    return result


# ============================================================
# STREAMING
# ============================================================

async def stream_email_agent(
    message: str,
    thread_id: str = "default",
    user_id: str = "default",
):

    try:

        memory_context = await memory_service.retrieve(
            user_id=user_id,
            query=message,
        )

    except Exception:

        logger.exception(
            "Memory retrieval failed during streaming"
        )

        memory_context = None

    prompt = SYSTEM_PROMPT

    if memory_context:

        prompt += f"""

IMPORTANT USER CONTEXT:

{memory_context}

Use this context silently when relevant.
"""

    agent = await _build_email_agent(
        prompt
    )

    assistant_response = ""

    async for chunk in agent.astream(
        {
            "messages": [
                (
                    "user",
                    message,
                )
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id,
            }
        },
        stream_mode="messages",
    ):

        yield chunk

        if (
            isinstance(chunk, tuple)
            and len(chunk) > 0
            and hasattr(
                chunk[0],
                "content",
            )
            and chunk[0].content
        ):

            assistant_response += (
                chunk[0].content
            )

    if assistant_response:

        asyncio.create_task(
            _remember_and_log(
                user_id=user_id,
                user_message=message,
                assistant_message=assistant_response,
            )
        )