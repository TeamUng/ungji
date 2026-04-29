"""
Async LLM judge — thin wrapper around the central fallback LLM client.

Sends a single structured prompt and parses the JSON response.
Each guard composes its own system prompt and calls `evaluate()`.

Error handling
--------------
- If all configured LLM providers are unreachable, `evaluate()` raises
  `LLMJudgeError`.  Guards catch this and apply their configured fallback
  policy (fail-open for input pre-screen, fail-safe for output evaluation).
- Temperature is requested as 0 for deterministic verdicts.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.clients.llm import LLMCallError, llm

logger = logging.getLogger(__name__)


class LLMJudgeError(Exception):
    """Raised when the judge call fails or returns unparseable output."""


class LLMJudge:
    """
    Calls the central fallback LLM with a structured evaluation prompt and
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

    def __init__(self, chat_model=None) -> None:
        self._llm = chat_model or llm

    async def evaluate(
        self,
        system_prompt: str,
        content: str,
    ) -> dict:
        """
        Send *content* with *system_prompt* as the system message.
        The system prompt must instruct the model to reply with JSON only.

        Returns the parsed JSON dict.
        Raises LLMJudgeError on any failure.
        """
        try:
            response = await self._llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=content),
                ],
                temperature=0,
            )
        except LLMCallError as exc:
            raise LLMJudgeError(f"LLM judge request failed: {exc}") from exc
        except Exception as exc:
            raise LLMJudgeError(f"LLM judge failed: {exc}") from exc

        raw_text = getattr(response, "content", "")
        try:
            return json.loads(_extract_json_object(raw_text))
        except json.JSONDecodeError as exc:
            logger.warning("LLM judge returned unparseable output: %s", raw_text)
            raise LLMJudgeError("Could not parse LLM judge response") from exc


def _extract_json_object(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    return _first_balanced_json_object(text) or text


def _first_balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]

        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    return None
