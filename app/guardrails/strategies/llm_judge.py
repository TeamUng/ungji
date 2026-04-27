"""
Async LLM judge — thin wrapper around Upstage Solar Pro.

Sends a single structured prompt and parses the JSON response.
Each guard composes its own system prompt and calls `evaluate()`.

Error handling
--------------
- If the API is unreachable or returns a bad response, `evaluate()` raises
  `LLMJudgeError`.  Guards catch this and apply their configured fallback
  policy (fail-open for input pre-screen, fail-safe for output evaluation).
- Temperature is fixed at 0 for deterministic verdicts.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0, connect=3.0)


class LLMJudgeError(Exception):
    """Raised when the Solar Pro call fails or returns unparseable output."""


class LLMJudge:
    """
    Calls Upstage Solar Pro with a structured evaluation prompt and
    returns the parsed JSON verdict dict.

    Usage::

        judge = LLMJudge()
        verdict = await judge.evaluate(
            system_prompt="You are a content safety judge ...",
            content="<student message here>",
        )
        # verdict is a dict, e.g.:
        # {
        #   "content_safety":   {"passed": true, "reason": null},
        #   "prompt_injection":  {"passed": false, "reason": "jailbreak attempt"},
        #   "topic_relevance":  {"passed": true, "reason": null},
        # }
    """

    def __init__(self, model: str = "solar-pro") -> None:
        self.model    = model
        self.base_url = settings.UPSTAGE_BASE_URL.rstrip("/")
        self.api_key  = settings.UPSTAGE_API_KEY

    async def evaluate(
        self,
        system_prompt: str,
        content: str,
    ) -> dict:
        """
        Send *content* to Solar Pro with *system_prompt* as the system message.
        The system prompt must instruct the model to reply with JSON only.

        Returns the parsed JSON dict.
        Raises LLMJudgeError on any failure.
        """
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": content},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type":  "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMJudgeError(
                f"Solar Pro returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise LLMJudgeError(f"Solar Pro request failed: {exc}") from exc

        raw = response.json()
        try:
            text = raw["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences if the model wraps the JSON
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            logger.warning("LLM judge returned unparseable output: %s", raw)
            raise LLMJudgeError("Could not parse LLM judge response") from exc
