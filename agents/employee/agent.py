"""Employee specialist: resolves employee information from the Employee DB."""
from __future__ import annotations

import json
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import get_settings
from .tools import search_employees


settings = get_settings()
employee_llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
)

EMPLOYEE_PROMPT = """
You are the Employee Agent.

Your only responsibility is employee-related information.

You have access to the search_employees tool.

Use search_employees whenever employee information
is required.

You can search employees by:

- name
- department
- job title
- email
- employee ID
- free-text query

Examples:

User:
"هات بيانات Ahmed Mohamed"

Use:
search_employees(name="Ahmed Mohamed")


User:
"هات كل الموظفين في IT"

Use:
search_employees(department="IT")


User:
"هات Software Engineers في IT"

Use:
search_employees(
    department="IT",
    job_title="Software Engineer"
)


User:
"مين صاحب omar@company.com؟"

Use:
search_employees(
    email="omar@company.com"
)

Do not send emails.

Do not read emails.

Do not perform Gmail operations.

Do not invent employee information.

Return concise factual results based only on
the Employee database.
"""


def _tool_records(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract structured records from the employee tool output."""

    for message in messages:

        if getattr(message, "type", None) != "tool":
            continue

        content = getattr(message, "content", None)

        if not content:
            continue

        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                continue

        if isinstance(content, dict):

            employee = content.get("employee")

            if isinstance(employee, dict):
                return [employee]

            matches = content.get("matches")

            if isinstance(matches, list):
                return [
                    item
                    for item in matches
                    if isinstance(item, dict)
                ]

        elif isinstance(content, list):

            for item in content:

                if not isinstance(item, dict):
                    continue

                if "employee" in item:
                    employee = item["employee"]

                    if isinstance(employee, dict):
                        return [employee]

    return []

async def run_employee_agent(message: str) -> dict[str, Any]:
    """Resolve employee data and return it in a supervisor-friendly shape."""
    agent = create_react_agent(
        model=employee_llm,
        tools=[search_employees],
        prompt=EMPLOYEE_PROMPT,
    )
    result = await agent.ainvoke({"messages": [("user", message)]})
    messages = result["messages"]
    for i, message in enumerate(messages):
        print("\n" + "=" * 60)
        print(f"MESSAGE {i}")
        print("TYPE:", type(message))
        print("MESSAGE TYPE:", getattr(message, "type", None))
        print("CONTENT:", repr(getattr(message, "content", None)))
        print("=" * 60)
    response = messages[-1].content
    if not isinstance(response, str):
        response = str(response)

    return {"records": _tool_records(messages), "summary": response}
