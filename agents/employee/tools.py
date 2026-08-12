from __future__ import annotations

from langchain_core.tools import tool

from database import get_connection


@tool
async def search_employee(name: str) -> dict:
    """
    Search for an employee by name in the Employee DB.

    Returns employee information including:
    employee ID, name, email, department and job title.
    """

    query = name.strip()

    if not query:
        return {
            "found": False,
            "matches": [],
            "message": "Employee name cannot be empty.",
        }

    async with get_connection() as connection:

        rows = await connection.fetch(
            """
            SELECT
                id,
                name,
                email,
                department,
                job_title
            FROM employees
            WHERE name ILIKE $1
            ORDER BY name
            """,
            f"%{query}%",
        )

    matches = [
        dict(row)
        for row in rows
    ]

    if not matches:
        return {
            "found": False,
            "matches": [],
            "message": (
                f"No employee found matching '{name}'."
            ),
        }

    if len(matches) > 1:
        return {
            "found": False,
            "ambiguous": True,
            "matches": matches,
            "message": (
                "Multiple employees matched the provided name."
            ),
        }

    return {
        "found": True,
        "employee": matches[0],
    }