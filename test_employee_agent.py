import asyncio

from agents.employee.agent import run_employee_agent


async def main():

    message = "هات بيانات Ahmed Mohamed"

    print("=" * 60)
    print("USER:")
    print(message)
    print("=" * 60)

    result = await run_employee_agent(message)

    print("\nEMPLOYEE AGENT RESULT")
    print("-" * 60)

    print("Records:")
    print(result["records"])

    print("\nSummary:")
    print(result["summary"])


if __name__ == "__main__":
    asyncio.run(main())