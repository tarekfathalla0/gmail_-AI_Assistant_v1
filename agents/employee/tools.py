from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from elasticsearch_client import get_elasticsearch


EMPLOYEE_INDEX = "employees"


@tool
async def search_employees(
    name: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
    email: str | None = None,
    employee_id: int | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Search employees in Elasticsearch.

    Use this tool whenever employee information is needed.

    Supported filters:

    - name
    - department
    - job_title
    - email
    - employee_id
    - free-text query

    Examples:

    name="Ahmed Mohamed"

    department="IT"

    department="IT", job_title="Software Engineer"

    email="ahmed@company.com"

    query="Khaled"
    """

    es = get_elasticsearch()

    must = []
    filters = []

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    if name:

        must.append(
            {
                "match": {
                    "name": {
                        "query": name,
                        "operator": "and",
                    }
                }
            }
        )

    # --------------------------------------------------------
    # Department
    # --------------------------------------------------------

    if department:

        filters.append(
            {
                "term": {
                    "department.keyword": department
                }
            }
        )

    # --------------------------------------------------------
    # Job title
    # --------------------------------------------------------

    if job_title:

        filters.append(
            {
                "term": {
                    "job_title.keyword": job_title
                }
            }
        )

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    if email:

        filters.append(
            {
                "term": {
                    "email.keyword": email
                }
            }
        )

    # --------------------------------------------------------
    # Employee ID
    # --------------------------------------------------------

    if employee_id is not None:

        filters.append(
            {
                "term": {
                    "id": employee_id
                }
            }
        )

    # --------------------------------------------------------
    # Free text
    # --------------------------------------------------------

    if query:

        must.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "name",
                        "email",
                        "department",
                        "job_title",
                    ],
                }
            }
        )

    # --------------------------------------------------------
    # Build query
    # --------------------------------------------------------

    bool_query: dict[str, Any] = {}

    if must:
        bool_query["must"] = must

    if filters:
        bool_query["filter"] = filters

    if not must and not filters:

        query_body = {
            "match_all": {}
        }

    else:

        query_body = {
            "bool": bool_query
        }

    # --------------------------------------------------------
    # Execute search
    # --------------------------------------------------------

    response = await es.search(
        index=EMPLOYEE_INDEX,
        query=query_body,
        size=min(limit, 100),
    )

    hits = response["hits"]["hits"]

    records = []

    for hit in hits:

        source = hit.get("_source", {})

        records.append(source)

    # --------------------------------------------------------
    # No results
    # --------------------------------------------------------

    if not records:

        return {
            "found": False,
            "matches": [],
            "message": "No employees matched the search criteria.",
        }

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    return {
        "found": True,
        "count": len(records),
        "matches": records,
    }