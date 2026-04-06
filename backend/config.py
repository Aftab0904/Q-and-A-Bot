# backend/config.py

EMBEDDING_MODELS = {
    "local": "all-MiniLM-L6-v2",
    "openai": "text-embedding-3-small"
}

LLM_MODELS = {
    "openai": "gpt-3.5-turbo",
    "groq": "llama3-8b-8192"
}

CURRENT_CONFIG = {
    "embedding": "local",
    "llm": "openai"
}