from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMModelConfig:
    provider: str
    model: str


# Non-secret model routing config lives here, not in .env.
# Provider values: upstage, openai, google. The LLM client also accepts gemini
# as an alias for google.
PRIMARY_LLM = LLMModelConfig(provider="upstage", model="solar-pro2")
FALLBACK_LLM: LLMModelConfig | None = None

LLM_TIMEOUT_SECONDS = 30.0
UPSTAGE_BASE_URL = "https://api.upstage.ai/v1/solar"
OPENAI_BASE_URL: str | None = None
