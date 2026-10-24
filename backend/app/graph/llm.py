from functools import lru_cache

from langchain_groq import ChatGroq

from app.config import settings


@lru_cache
def get_llm() -> ChatGroq:
    """Create the model client on first use (so the app can start even before a key is set)."""
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0,   # we want the same question to give the same query
        timeout=30,
        max_retries=2,
    )