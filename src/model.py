from config import (
    LLM_PROVIDER, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
    EMBEDDING_PROVIDER, EMBEDDING_API_KEY, EMBEDDING_BASE_URL, EMBEDDING_MODEL,
)


def create_llm(provider: str | None = None, **kwargs):
    provider = (provider or LLM_PROVIDER).lower()
    api_key = kwargs.pop("api_key", LLM_API_KEY)
    base_url = kwargs.pop("base_url", LLM_BASE_URL)
    model = kwargs.pop("model", LLM_MODEL)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(api_key=api_key, base_url=base_url, model=model, **kwargs)

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(api_key=api_key, model=model, **kwargs)

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(base_url=base_url, model=model, **kwargs)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(api_key=api_key, base_url=base_url, model=model, **kwargs)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(api_key=api_key, model=model, **kwargs)

    raise ValueError(f"Unsupported LLM provider: {provider}")


def create_embeddings(provider: str | None = None, **kwargs):
    provider = (provider or EMBEDDING_PROVIDER).lower()
    api_key = kwargs.pop("api_key", EMBEDDING_API_KEY)
    base_url = kwargs.pop("base_url", EMBEDDING_BASE_URL)
    model = kwargs.pop("model", EMBEDDING_MODEL)

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=model, base_url=base_url, **kwargs)

    if provider in ("openai", "groq"):
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(api_key=api_key, base_url=base_url, model=model, **kwargs)

    if provider == "jina":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            api_key=api_key,
            base_url=base_url or "https://api.jina.ai/v1",
            model=model or "jina-embeddings-v3",
            **kwargs,
        )

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(api_key=api_key, model=model, **kwargs)

    raise ValueError(f"Unsupported embedding provider: {provider}")


default_llm = create_llm()
default_embeddings = create_embeddings()
