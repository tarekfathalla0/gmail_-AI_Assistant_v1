from __future__ import annotations

import logging

from langgraph.store.base import BaseStore
from langgraph.store.postgres import AsyncPostgresStore

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_store_cm: AsyncPostgresStore | None = None
store: BaseStore | None = None


async def initialize_store() -> BaseStore:
    """
    Initialize the shared LangGraph/LangMem store.

    This should be called once during application startup.
    """

    global _store_cm, store

    if store is not None:
        return store

    logger.info("Initializing PostgreSQL memory store...")

    _store_cm = AsyncPostgresStore.from_conn_string(
        settings.DATABASE_URL
    )

    store = await _store_cm.__aenter__()

    # Create the required tables/indexes if they do not exist.
    await store.setup()

    logger.info("Memory store initialized.")

    return store


async def shutdown_store() -> None:
    """
    Close the shared store.

    This should be called during application shutdown.
    """

    global _store_cm, store

    if _store_cm is None:
        return

    logger.info("Closing memory store...")

    await _store_cm.__aexit__(None, None, None)

    _store_cm = None
    store = None

    logger.info("Memory store closed.")


def get_store() -> BaseStore:
    """
    Return the initialized store.

    Raises:
        RuntimeError: if initialize_store() has not been called.
    """

    if store is None:
        raise RuntimeError(
            "Memory store has not been initialized. "
            "Call initialize_store() during application startup."
        )

    return store