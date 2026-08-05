from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from config import get_settings

settings = get_settings()

checkpointer_cm = AsyncPostgresSaver.from_conn_string(
    settings.DATABASE_URL
)

checkpointer = None