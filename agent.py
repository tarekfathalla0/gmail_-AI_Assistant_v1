from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from types import SimpleNamespace

from config import get_settings
from data import checkpoint
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
"""


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

    tools = await get_mcp_tools()

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
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=prompt,
        checkpointer=checkpoint.checkpointer,
    )

    result = await agent.ainvoke(
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
    )

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
    tools = await get_mcp_tools()

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

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=prompt,
        checkpointer=checkpoint.checkpointer,
    )

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