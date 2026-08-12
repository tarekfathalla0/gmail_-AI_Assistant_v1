import asyncio

from agents.supervisor.agent import get_supervisor_decision


async def test(message: str):

    print("\n" + "=" * 70)
    print("USER:")
    print(message)

    decision = await get_supervisor_decision(message)

    print("\nSUPERVISOR DECISION:")
    print("Next Agent:", decision.next_agent)
    print("Reason:", decision.reason)


async def main():

    await test(
        "هات بيانات Ahmed Mohamed"
    )

    await test(
        "اقرأ آخر 5 إيميلات عندي"
    )

    await test(
        "هات إيميل Ahmed Mohamed وابعتله إن الاجتماع اتأجل لبكرة"
    )


if __name__ == "__main__":
    asyncio.run(main())