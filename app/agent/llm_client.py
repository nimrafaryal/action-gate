"""
Minimal client for an OpenAI-compatible chat endpoint.

AMD Token Factory / AMD Developer Cloud (vLLM) expose an OpenAI-compatible
API, so we only need base URL, API key and model name. All values come
from environment variables so no secrets live in the code.
"""

import os

import requests


class LLMNotConfigured(RuntimeError):
    """Raised when no AMD model endpoint is configured."""


def _load_dotenv() -> None:
    """Tiny .env loader (avoids an extra dependency)."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_dotenv()


def get_config() -> dict:
    return {
        "base_url": os.getenv("AMD_BASE_URL", "").rstrip("/"),
        "api_key": os.getenv("AMD_API_KEY", ""),
        "model": os.getenv("AMD_MODEL", ""),
    }


def is_configured() -> bool:
    cfg = get_config()
    return bool(cfg["base_url"] and cfg["model"])


def chat(messages: list[dict], temperature: float = 0.0, timeout: int = 60) -> str:
    """Send a chat completion request and return the assistant text."""
    cfg = get_config()
    if not (cfg["base_url"] and cfg["model"]):
        raise LLMNotConfigured("Set AMD_BASE_URL and AMD_MODEL in .env")

    headers = {"Content-Type": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    response = requests.post(
        f"{cfg['base_url']}/chat/completions",
        headers=headers,
        json={
            "model": cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 800,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
