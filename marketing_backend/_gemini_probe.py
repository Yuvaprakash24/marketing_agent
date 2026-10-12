import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketing_backend.settings")
django.setup()


def step(label, fn):
    print(label, flush=True)
    try:
        print("  ->", repr(fn())[:160], flush=True)
    except Exception as exc:
        print("  !! FAILED", type(exc).__name__, str(exc)[:200], flush=True)


from utils.chat_openrouter import get_gemini_llm

step(
    "Gemini direct via langchain:",
    lambda: get_gemini_llm().invoke("Reply with exactly: OK").content.strip(),
)
print("done", flush=True)
sys.stdout.flush()
