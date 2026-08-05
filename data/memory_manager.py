from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langmem import create_memory_store_manager
from config import Settings
from data.memory import get_store
from data.schemas import (
    SemanticMemory,
    EpisodicMemory,
    ProceduralMemory,
)

settings = Settings()
logger = logging.getLogger(__name__)


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
)


class MemoryManager:
    def __init__(self) -> None:
        self._manager = None

    @property
    def manager(self):
        if self._manager is None:
            self._manager = create_memory_store_manager(
                llm,
                store=get_store(),
                schemas=[
                    SemanticMemory,
                    EpisodicMemory,
                    ProceduralMemory,
                ],
            )
        return self._manager

    async def retrieve(
    self,
    *,
    namespace: tuple[str, ...],
    query: str,
    limit: int = 5,
):
        return await self.manager.search(
            query=query,
            limit=limit,
            config=RunnableConfig(
                configurable={
                    "namespace": namespace,
                }
            ),
        )

    async def extract(
        self,
        *,
        namespace: tuple[str, ...],
        messages: list[dict[str, Any]],
    ):
            return await self.manager.ainvoke(
        {
            "messages": messages,
        },
        config=RunnableConfig(
            configurable={
                "namespace": namespace,
            }
        ),
    )

memory_manager = MemoryManager()