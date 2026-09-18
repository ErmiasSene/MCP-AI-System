# save as test_models.py
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

models_to_test = [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "gemma2-9b-it",
]

print("Testing Groq models...\n")

for model in models_to_test:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10,
        )
        print(f"✅ {model}: WORKS")
    except Exception as e:
        error_msg = str(e)
        if "decommissioned" in error_msg or "not found" in error_msg.lower():
            print(f"❌ {model}: DECOMMISSIONED/NOT FOUND")
        elif "rate limit" in error_msg.lower():
            print(f"⚠️  {model}: RATE LIMITED (but exists)")
        else:
            print(f"❌ {model}: {error_msg[:80]}")