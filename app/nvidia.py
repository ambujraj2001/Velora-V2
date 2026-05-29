from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings

from app.config import settings


def get_llm() -> ChatNVIDIA:
    return ChatNVIDIA(
        model=settings.nvidia_model,
        api_key=settings.nvidia_api_key,
        temperature=0.0
    )


def get_embedder() -> NVIDIAEmbeddings:
    return NVIDIAEmbeddings(
        model=settings.nvidia_embedding_model,
        api_key=settings.nvidia_api_key,
    )
