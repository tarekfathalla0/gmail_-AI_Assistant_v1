from langchain_openai import ChatOpenAI
from langmem.knowledge import create_memory_searcher

from config import get_settings

settings = get_settings()

llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
)

memory_searcher = create_memory_searcher(
    model=llm,
)