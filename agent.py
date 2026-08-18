from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool
from langgraph.types import Command, interrupt
from types import SimpleNamespace

from config import get_settings
#from data import checkpoint
from langgraph.checkpoint.memory import InMemorySaver
from data.memory_service import memory_service
from mcp_client import get_mcp_tools

settings = get_settings()

# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     google_api_key=settings.GEMINI_API_KEY,
# )

llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
)

checkpoint = InMemorySaver()

SYSTEM_PROMPT = """
You are an intelligent Gmail AI assistant.

You have access to long-term memory retrieved from previous conversations.
Use memories silently to personalize your responses.

Never say:
- "I cannot remember"
- "I don't have memory"
- "I cannot store information"

If relevant memories exist, apply them naturally.
Do not explain the memory system.

Memory rules:
- Treat the provided memories as trusted user context.
- Use them naturally when answering.
- Do not say "I cannot remember".
- Do not say "I don't have memory".
- Do not mention the existence of memory systems.
- Do not explain where the information came from unless the user explicitly asks.

The memories can contain:
- Semantic memory: facts about the user.
- Episodic memory: previous interactions.
- Procedural memory: user preferences and instructions.

If a memory contains a user preference, follow it.
If no relevant memory exists, answer normally.

Professional email rules:
- When sending an email, write a clear, specific subject line.
- Use the user's language unless they request another language.
- Structure the body as: appropriate greeting, concise purpose, relevant
  details or requested action, and a professional closing.
- Keep the tone polite, direct, and business-appropriate.
- Use short paragraphs and do not add unnecessary filler.
- Never invent names, dates, facts, commitments, or contact details.
- If the recipient, purpose, or essential details are unclear, ask for them
  before preparing the email.
- Do not include placeholders such as "[Name]" unless the user explicitly
  provides or requests one.
- Do not invent a signature.
- For follow-ups or requests, state the requested next step and deadline
  when the user supplied one.

Email formatting example:

User request:
"ابعت لأحمد إن الاجتماع اتأجل لبكرة واطلب منه يأكد إن الوقت الجديد مناسب."

Expected email:

To: ahmed@company.com
Subject: Meeting Rescheduled to Tomorrow

Dear Ahmed,

I wanted to let you know that the meeting has been rescheduled to tomorrow.

Please confirm whether the new timing works for you.

Best regards,
Tarek

Important:
- The example above is only a formatting and style reference.
- Never copy its recipient, name, date, subject, body, or signature into
  another email unless the user explicitly provides the same information.
- Generate the email based only on the current user's request and trusted
  context.
- Before sending an email, make sure the recipient, subject, and body are
  clearly defined.
- The email must be ready for human review before it is sent.
"""


def _approval_response(to: str, subject: str, body: str) -> str:
    return (
        "Email ready for approval:\n"
        f"To: {to}\n"
        f"Subject: {subject}\n"
        f"Body:\n{body}\n\n"
        "Reply with 'approve' to send, 'cancel' to discard, "
        "or 'edit: <new body>' to revise it."
    )


def _approval_decision(value) -> tuple[str, str | None]:
    if isinstance(value, dict):
        return str(value.get("action", "")).lower(), value.get("body")

    text = str(value).strip()
    lower = text.lower()
    if lower in {"approve", "approved", "yes", "send", "ok"}:
        return "approve", None
    if lower in {"cancel", "cancelled", "canceled", "no", "discard"}:
        return "cancel", None
    if lower.startswith("edit:"):
        return "edit", text[5:].strip()
    return "edit", text


def _email_tools(tools):
    send_tool = next(tool for tool in tools if tool.name == "send_email")

    async def send_email_with_approval(to: str, subject: str, body: str):
        approval = interrupt({
            "type": "email_approval",
            "to": to,
            "subject": subject,
            "body": body,
        })
        action, edited_body = _approval_decision(approval)

        if action == "cancel":
            return "Email cancelled."

        if action == "edit":
            body = edited_body or body
            approval = interrupt({
                "type": "email_approval",
                "to": to,
                "subject": subject,
                "body": body,
            })
            action, edited_body = _approval_decision(approval)
            if action == "cancel":
                return "Email cancelled."
            if action == "edit":
                return "Email still needs approval."

        return await send_tool.ainvoke({
            "to": to,
            "subject": subject,
            "body": body,
        })

    approval_tool = StructuredTool.from_function(
        coroutine=send_email_with_approval,
        name="send_email",
        description=(
            "Prepare an email for human approval before sending it. "
            "Use a clear professional subject and body with a greeting, "
            "concise purpose, requested action, and closing. "
            "Never send an email without approval."
        ),
        args_schema=send_tool.args_schema,
    )
    return [
        approval_tool if tool.name == "send_email" else tool
        for tool in tools
    ]


async def _build_email_agent(prompt: str = SYSTEM_PROMPT):
    tools = _email_tools(await get_mcp_tools())
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=prompt,
        checkpointer=checkpoint,
    )


async def has_pending_email_approval(thread_id: str) -> bool:
    agent = await _build_email_agent()
    snapshot = await agent.aget_state(
        {"configurable": {"thread_id": thread_id}}
    )
    return any(task.interrupts for task in getattr(snapshot, "tasks", ()))


async def run_email_agent(
    message: str,
    thread_id: str = "default",
    user_id: str = "default",
):
    # Handle explicit forget commands from the user: "forget <query>"
    m = message.strip()
    lower = m.lower()

    if lower.startswith("forget "):
        query = m[7:].strip()
        deleted = await memory_service.forget(user_id=user_id, query=query)
        if deleted == -1:
            return {
                "messages": [
                    SimpleNamespace(
                        content=(
                            "I found many possible matches for that phrase — "
                            "please be more specific or confirm the exact text you want forgotten."
                        )
                    )
                ]
            }
        if deleted == -2:
            return {"messages": [SimpleNamespace(content=f"No exact matches found for: {query}")]} 

        return {"messages": [SimpleNamespace(content=f"Okay — deleted {deleted} matching memory(ies) for: {query}" )]}

    if lower in ("forget it", "forget that"):
        return {"messages": [SimpleNamespace(content="Please tell me what you'd like me to forget, e.g. 'forget I like coffee'.")]} 

    memory_context = await memory_service.retrieve(
        user_id=user_id,
        query=message,
    )
    print("========== MEMORY CONTEXT ==========")
    print(memory_context)
    print("====================================")

    prompt = SYSTEM_PROMPT

    if memory_context:
        prompt += f"""

        IMPORTANT USER CONTEXT:

        {memory_context}

        Instructions:
        - The above information is already known context.
        - Never claim you cannot remember.
        - Never mention limitations about memory.
        - Apply these preferences directly in your answer.
        """
    agent = await _build_email_agent(prompt)
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    snapshot = await agent.aget_state(config)
    invoke_input = (
        Command(resume=message)
        if any(task.interrupts for task in getattr(snapshot, "tasks", ()))
        else {"messages": [("user", message)]}
    )

    result = await agent.ainvoke(invoke_input, config=config)

    interrupts = result.get("__interrupt__", ())
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

    assistant_message = result["messages"][-1].content

    await memory_service.remember(
        user_id=user_id,
        user_message=message,
        assistant_message=assistant_message,
    )

    return result


async def stream_email_agent(
    message: str,
    thread_id: str = "default",
    user_id: str = "default",
):
    memory_context = await memory_service.retrieve(
        user_id=user_id,
        query=message,
    )

    prompt = SYSTEM_PROMPT

    if memory_context:
        prompt += f"""

        User context from previous interactions:

        {memory_context}

        Use this context silently when relevant.
        """

    agent = await _build_email_agent(prompt)

    assistant_response = ""

    async for chunk in agent.astream(
        {
            "messages": [
                ("user", message),
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
            and hasattr(chunk[0], "content")
            and chunk[0].content
        ):
            assistant_response += chunk[0].content

    if assistant_response:
        await memory_service.remember(
            user_id=user_id,
            user_message=message,
            assistant_message=assistant_response,
        )