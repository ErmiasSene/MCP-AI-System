import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM provider: "gemini" or "groq"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    
    # Groq credentials
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Gemini credentials (backup)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Model selection
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    
    # Database
    DB_URL: str = "sqlite:///./data/shop.db"
    
    # RAG
    CHROMA_DIR: str = "./data/chroma"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache()
def get_settings():
    return Settings()