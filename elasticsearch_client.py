from __future__ import annotations

from elasticsearch import AsyncElasticsearch

from config import get_settings


settings = get_settings()

_es: AsyncElasticsearch | None = None


async def connect_elasticsearch() -> None:

    global _es

    if _es is not None:
        return

    _es = AsyncElasticsearch(
        settings.ELASTICSEARCH_URL
    )

    if not await _es.ping():
        raise RuntimeError(
            "Could not connect to Elasticsearch."
        )

    print("Elasticsearch connected.")


async def close_elasticsearch() -> None:

    global _es

    if _es is None:
        return

    await _es.close()

    _es = None


def get_elasticsearch() -> AsyncElasticsearch:

    if _es is None:
        raise RuntimeError(
            "Elasticsearch has not been initialized. "
            "Call connect_elasticsearch() during application startup."
        )

    return _es