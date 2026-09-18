"""Groq client with native tool-calling support, automatic retry, and model fallback."""
import json
import time
from functools import lru_cache
from groq import Groq, RateLimitError, NotFoundError
from app.config import get_settings


# Models known to be active on Groq (updated for 2025)
SUPPORTED_MODELS = [
    "qwen/qwen3.8-27b",          # Your working model
    "gemma2-9b-it",               # Google's model, often available
    "llama-3.2-11b-vision-preview",  # Vision model, might work
]

# Models retired/decommissioned — never use these
DECOMMISSIONED_MODELS = {
    "mixtral-8x7b-32768",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "llama-3.1-8b-instant",  # Your key doesn't have access
    "llama-3.1-70b-versatile",
    "llama-3.2-1b-preview",
    "llama-3.2-3b-preview",
}


@lru_cache()
def client():
    """Create a cached Groq client."""
    s = get_settings()
    if not s.GROQ_API_KEY.startswith("gsk_"):
        raise RuntimeError(
            "Set GROQ_API_KEY in .env (get a free key at https://console.groq.com/keys)"
        )
    
    # Warn if using a decommissioned model
    if s.LLM_MODEL in DECOMMISSIONED_MODELS:
        print(f"[WARNING] Model '{s.LLM_MODEL}' is decommissioned. "
              f"Will fall back to: {SUPPORTED_MODELS[0]}")
    
    return Groq(api_key=s.GROQ_API_KEY)


def _retry_with_backoff(func, max_retries=3):
    """Retry a function on rate limit errors with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = min(2 ** attempt, 10)
            print(f"[RETRY] Rate limited, waiting {wait_time}s "
                  f"(attempt {attempt + 1}/{max_retries})")
            time.sleep(wait_time)


def _get_models_to_try():
    """Build the list of models to try: primary + fallbacks."""
    s = get_settings()
    primary = s.LLM_MODEL
    
    # Start with primary
    models = [primary]
    
    # Add fallbacks (skip decommissioned and primary)
    for m in SUPPORTED_MODELS:
        if m != primary and m not in DECOMMISSIONED_MODELS:
            models.append(m)
        if len(models) >= 3:  # Try up to 3 models total
            break
    
    return models


def chat_with_tools(messages, tools, temperature=0.2, max_tokens=2000):
    """
    Single turn with tool-calling. Returns the completion message.
    Automatically retries on rate limits and falls back to alternative models.
    """
    models_to_try = _get_models_to_try()
    last_error = None
    
    for i, model in enumerate(models_to_try):
        def _call(m=model):
            return client().chat.completions.create(
                model=m,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
            ).choices[0].message
        
        try:
            result = _retry_with_backoff(_call)
            s = get_settings()
            if model != s.LLM_MODEL:
                print(f"[FALLBACK] Used model '{model}' instead of '{s.LLM_MODEL}'")
            return result
        
        except NotFoundError as e:
            last_error = e
            print(f"[MODEL] '{model}' not available, trying next...")
            continue
        
        except RateLimitError as e:
            last_error = e
            print(f"[RATE LIMIT] '{model}' exhausted retries, trying next...")
            continue
        
        except Exception as e:
            last_error = e
            break
    
    raise last_error or RuntimeError("All models failed")


def chat_text(messages, temperature=0.2, max_tokens=2000):
    """
    Simple text completion without tools.
    Automatically retries on rate limits and falls back to alternative models.
    """
    models_to_try = _get_models_to_try()
    last_error = None
    
    for i, model in enumerate(models_to_try):
        def _call(m=model):
            return client().chat.completions.create(
                model=m,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ).choices[0].message.content
        
        try:
            result = _retry_with_backoff(_call)
            s = get_settings()
            if model != s.LLM_MODEL:
                print(f"[FALLBACK] Used model '{model}' instead of '{s.LLM_MODEL}'")
            return result
        
        except NotFoundError as e:
            last_error = e
            print(f"[MODEL] '{model}' not available, trying next...")
            continue
        
        except RateLimitError as e:
            last_error = e
            print(f"[RATE LIMIT] '{model}' exhausted retries, trying next...")
            continue
        
        except Exception as e:
            last_error = e
            break
    
    raise last_error or RuntimeError("All models failed")