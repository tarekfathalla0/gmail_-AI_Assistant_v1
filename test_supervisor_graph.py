import asyncio
import selectors
from agents.supervisor.graph import supervisor_graph
from mcp_client import initialize_mcp_tools
from data.memory import initialize_store
from database import close as close_database, connect as connect_database

async def main():

    # Initialize Gmail MCP
    await initialize_mcp_tools()

    # Initialize Memory Store
    await connect_database()
    await initialize_store()

    message = (
        "هات إيميل Ahmed Mohamed "
        "وابعتله إن الاجتماع اتأجل لبكرة"
    )

    print("\n")
    print("=" * 70)
    print("USER:")
    print(message)
    print("=" * 70)

    result = await supervisor_graph.ainvoke(
        {
            "messages": [
                (
                    "user",
                    message,
                )
            ],
            "user_id": "test-user",
            "thread_id": "test-thread",
            "next_agent": None,
            "employee_result": None,
            "gmail_result": None,
            "final_response": None,
            "step_count": 0,
        }
    )

    print("\n")
    print("=" * 70)
    print("FINAL RESPONSE")
    print("=" * 70)

    print(result["final_response"])


if __name__ == "__main__":
    

    asyncio.run(
        main(),
        loop_factory=lambda: asyncio.SelectorEventLoop(
            selectors.SelectSelector()
        ),
    )