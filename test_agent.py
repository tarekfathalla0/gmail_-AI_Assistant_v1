import asyncio

from agent import run_email_agent


async def main():

    result = await run_email_agent(
        "Show me my latest 5 emails"
    )

    print(
        result["messages"][-1].content
    )


if __name__ == "__main__":
    asyncio.run(main())