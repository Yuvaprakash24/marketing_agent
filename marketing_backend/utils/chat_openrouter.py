"""LLM construction.

OpenRouter is the primary provider. Its ``:free`` model variants draw from a rate
limit pool shared across all OpenRouter users, so they return 429 under load; when
that happens we retry briefly, then fall back to Gemini with ``GOOGLE_API_KEY``.
"""

import asyncio
import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-r1-0528:free")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-latest")
MAX_RETRIES = 2


class ChatOpenRouter(ChatOpenAI):
    """ChatOpenAI pointed at OpenRouter so any OpenRouter model can be used."""

    openai_api_base: str
    openai_api_key: SecretStr
    model_name: str = DEFAULT_MODEL

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        openai_api_key: Optional[str] = None,
        openai_api_base: str = "https://openrouter.ai/api/v1",
        **kwargs,
    ):
        openai_api_key = openai_api_key or os.getenv('OPENROUTER_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        super().__init__(
            openai_api_base=openai_api_base,
            openai_api_key=SecretStr(openai_api_key),
            model_name=model_name,
            **kwargs,
        )


class LlmWithFallback:
    """Tries the primary model, then Gemini, so a 429 does not kill generation."""

    def __init__(self, primary, fallback=None):
        self.primary = primary
        self.fallback = fallback

    async def ainvoke(self, prompt, **kwargs):
        return await self._call(prompt, **kwargs)

    def invoke(self, prompt, **kwargs):
        return self._call_sync(prompt, **kwargs)

    def _call_sync(self, prompt, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return self.primary.invoke(prompt, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not _is_rate_limit(exc) or attempt == MAX_RETRIES:
                    break
                _sleep_backoff(attempt)
                logger.warning("Primary LLM rate-limited; retrying (%s/%s)", attempt + 1, MAX_RETRIES)

        if self.fallback and last_error is not None:
            logger.warning("Primary LLM failed; using Gemini fallback: %s", last_error)
            return self.fallback.invoke(prompt, **kwargs)
        raise last_error

    async def _call(self, prompt, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return await self.primary.ainvoke(prompt, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not _is_rate_limit(exc) or attempt == MAX_RETRIES:
                    break
                await asyncio.sleep(2 * (attempt + 1))
                logger.warning("Primary LLM rate-limited; retrying (%s/%s)", attempt + 1, MAX_RETRIES)

        if self.fallback and last_error is not None:
            logger.warning("Primary LLM failed; using Gemini fallback: %s", last_error)
            return await self.fallback.ainvoke(prompt, **kwargs)
        raise last_error


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        getattr(exc, "status_code", None) == 429
        or "429" in text
        or "rate-limited" in text
        or "rate_limit" in text
        or "rate limit" in text
    )


def _sleep_backoff(attempt: int) -> None:
    time.sleep(2 * (attempt + 1))


def get_openrouter_llm(**kwargs):
    kwargs.setdefault("temperature", 0.7)
    kwargs.setdefault("max_tokens", 2048)
    return ChatOpenRouter(**kwargs)


def get_gemini_llm(**kwargs):
    """Gemini called directly, used as the fallback provider."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    return ChatGoogleGenerativeAI(
        model=kwargs.pop("model_name", FALLBACK_MODEL),
        google_api_key=api_key,
        temperature=kwargs.pop("temperature", 0.7),
        max_output_tokens=kwargs.pop("max_tokens", 2048),
        **kwargs,
    )


def get_llm(model_name: str = DEFAULT_MODEL, **kwargs):
    """The LLM every agent should use: OpenRouter, falling back to Gemini.

    Whichever providers are configured get used, so the app still runs with only
    one of the two keys present. ``model_name`` names an OpenRouter model and is
    deliberately not forwarded to Gemini, which has its own model namespace.
    """
    primary = None
    try:
        primary = get_openrouter_llm(model_name=model_name, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OpenRouter unavailable: %s", exc)

    fallback = None
    try:
        fallback = get_gemini_llm(**kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini fallback unavailable: %s", exc)

    if primary and fallback:
        return LlmWithFallback(primary, fallback)
    if primary:
        return LlmWithFallback(primary)
    if fallback:
        logger.info("Using Gemini as the primary LLM")
        return fallback

    raise ValueError(
        "No LLM configured. Set OPENROUTER_API_KEY or GOOGLE_API_KEY."
    )
