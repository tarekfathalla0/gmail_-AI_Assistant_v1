from data import memory
from data.memory_manager import memory_manager
from data.searcher import memory_searcher


def namespace(
    user_id: str,
):
    return (
        "users",
        user_id,
    )


async def save_memories(
    user_id: str,
    messages,
):
    return await memory_manager.ainvoke(
        {
            "messages": messages,
        },
        config={
            "configurable": {
                "langgraph_user_id": user_id,
            }
        },
    )

async def search_memories(
    user_id: str,
    message: str,
):
    return await memory_searcher.ainvoke(
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
                "langgraph_user_id": user_id,
            }
        },
    )