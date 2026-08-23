from __future__ import annotations

from datetime import UTC, datetime
import asyncio
import string
from uuid import uuid4

from data.memory import get_store
from data.memory_extractor import memory_extractor
from data.schemas import Memory, MemoryType


class MemoryService:
    def __init__(self) -> None:
        self._store = get_store

    async def remember(
        self,
        *,
        user_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        memories = await memory_extractor.extract(
            user_message=user_message,
            assistant_message=assistant_message,
        )

        await asyncio.gather(
            self._save(
                user_id=user_id,
                memory_type=MemoryType.SEMANTIC,
                memories=memories.semantic,
            ),
            self._save(
                user_id=user_id,
                memory_type=MemoryType.EPISODIC,
                memories=memories.episodic,
            ),
            self._save(
                user_id=user_id,
                memory_type=MemoryType.PROCEDURAL,
                memories=memories.procedural,
            ),
        )

    async def retrieve(
        self,
        *,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> str:
        sections = []

        results_by_type = await asyncio.gather(
            *(
                self._store().asearch(
                    ("users", user_id, memory_type.value),
                    query=query,
                    limit=limit,
                )
                for memory_type in MemoryType
            )
        )

        for memory_type, results in zip(MemoryType, results_by_type):

            if not results:
                continue

            sections.append(f"{memory_type.value.title()} Memories:")

            for item in results:
                value = item.value
                sections.append(f"- {value['content']}")

            sections.append("")

        return "\n".join(sections).strip()

    async def _save(
        self,
        *,
        user_id: str,
        memory_type: MemoryType,
        memories: list[str],
    ) -> None:
        store = self._store()

        for content in memories:
            memory = Memory(
                id=str(uuid4()),
                type=memory_type,
                content=content,
                importance=0.5,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            existing = await store.asearch(
                ("users", user_id, memory_type.value),
                query=content,
                limit=3,
            )

            duplicate = False

            for item in existing:
                if item.value["content"].lower() == content.lower():
                    duplicate = True
                    break

            if duplicate:
                continue
            await store.aput(
                namespace=("users", user_id, memory_type.value),
                key=memory.id,
                value=memory.model_dump(mode="json"),
            )
            print("SAVED MEMORY:")
            print(memory.model_dump())

    async def forget(self, *, user_id: str, query: str) -> int:
        """Delete memories matching `query` for the given `user_id`.

        Returns the number of deleted items.
        """
        store = self._store()
        deleted = 0

        if not query or not query.strip():
            return -2

        def _normalize(s: str) -> str:
            if not s:
                return ""
            s = s.strip().lower()
            s = s.translate(str.maketrans("", "", string.punctuation))
            s = " ".join(s.split())
            return s

        query_norm = _normalize(query)

        exact_matches: list[tuple[str, object, str]] = []
        fuzzy_count = 0

        for memory_type in MemoryType:
            try:
                results = await store.asearch(
                    ("users", user_id, memory_type.value),
                    query=query,
                    limit=50,
                )
            except Exception:
                continue

            if not results:
                continue

            fuzzy_count += len(results)

            for item in results:
                key = getattr(item, "key", None) or item.value.get("id")
                content = (item.value.get("content") or "").strip()

                if not key or not content:
                    continue

                if _normalize(content) == query_norm:
                    exact_matches.append((memory_type.value, item, key))

        # If we have exact matches, delete only those
        if exact_matches:
            for ns, item, key in exact_matches:
                try:
                    delete_fn = getattr(store, "adelete")
                    await delete_fn(("users", user_id, ns), key)
                    deleted += 1
                    continue
                except AttributeError:
                    pass
                except Exception:
                    pass

                try:
                    await store.aput(
                        namespace=("users", user_id, ns),
                        key=key,
                        value={"content": ""},
                    )
                    deleted += 1
                except Exception:
                    continue

            return deleted

        # No exact matches; if many fuzzy results were found, abort to avoid mass-deletes
        if fuzzy_count > 5:
            return -1

        # Otherwise, do not delete ambiguous fuzzy matches without confirmation
        return -2


memory_service = MemoryService()


async def _forget_wrapper(user_id: str, query: str) -> int:
    """Compatibility wrapper to allow calling forget as module-level function.

    Returns the number of deleted items.
    """
    return await memory_service.forget(user_id=user_id, query=query)
