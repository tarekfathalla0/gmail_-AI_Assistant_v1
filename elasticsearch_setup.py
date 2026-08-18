from __future__ import annotations

from elasticsearch_client import get_elasticsearch
from database import get_connection


EMPLOYEE_INDEX = "employees"


EMPLOYEE_MAPPING = {
    "properties": {
        "id": {
            "type": "integer",
        },
        "name": {
            "type": "text",
            "fields": {
                "keyword": {
                    "type": "keyword",
                }
            },
        },
        "email": {
            "type": "text",
            "fields": {
                "keyword": {
                    "type": "keyword",
                }
            },
        },
        "department": {
            "type": "text",
            "fields": {
                "keyword": {
                    "type": "keyword",
                }
            },
        },
        "job_title": {
            "type": "text",
            "fields": {
                "keyword": {
                    "type": "keyword",
                }
            },
        },
    }
}


async def initialize_employees_index() -> None:

    es = get_elasticsearch()

    exists = await es.indices.exists(
        index=EMPLOYEE_INDEX
    )

    if not exists:

        await es.indices.create(
            index=EMPLOYEE_INDEX,
            mappings=EMPLOYEE_MAPPING,
        )

        print(
            f"Created Elasticsearch index: {EMPLOYEE_INDEX}"
        )

    else:

        print(
            f"Elasticsearch index already exists: "
            f"{EMPLOYEE_INDEX}"
        )


async def sync_employees() -> None:

    es = get_elasticsearch()

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
            ORDER BY id
            """
        )

    if not rows:
        print("No employees found in PostgreSQL.")
        return

    operations = []

    for employee in rows:

        operations.append(
            {
                "index": {
                    "_index": EMPLOYEE_INDEX,
                    "_id": str(employee["id"]),
                }
            }
        )

        operations.append(
            {
                "id": employee["id"],
                "name": employee["name"],
                "email": employee["email"],
                "department": employee["department"],
                "job_title": employee["job_title"],
            }
        )

    response = await es.bulk(
        operations=operations,
        refresh="wait_for",
    )

    if response["errors"]:
        raise RuntimeError(
            "Some employees failed to sync to Elasticsearch."
        )

    print(
        f"Synced {len(rows)} employees "
        f"from PostgreSQL to Elasticsearch."
    )