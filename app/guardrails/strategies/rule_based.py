"""
Fast, synchronous rule-based checks using regex and keyword matching.

These run before any LLM call to catch obvious violations cheaply (~0 ms).
All functions are pure and stateless — no I/O, no async.

Design note — topic verdict
---------------------------
quick_topic_verdict intentionally does NOT try to pass messages as "on_topic"
based on keyword matching.  A student could mention a study word while asking
for something completely off-topic (e.g. "tell me a game cheat code, I already
did my 수학 homework").  Keyword presence is therefore used only as a signal
for "off_topic" (two or more clearly off-topic terms), never as a positive
pass.  Everything ambiguous is deferred to the LLM judge.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Profanity / inappropriate content
# ---------------------------------------------------------------------------

_PROFANITY_PATTERNS = [
    # Korean profanity (common examples — expand in production)
    r"시발|씨발|ㅅㅂ",
    r"병신|ㅂㅅ",
    r"개새끼|개색끼",
    r"존나|졸라",
    r"미친놈|미친년",
    # English profanity
    r"\b(fuck|shit|bullshit|ass(?:hole)?|bitch|bastard|crap)\b",
]

_PROFANITY_RE = [
    re.compile(p, re.IGNORECASE | re.UNICODE) for p in _PROFANITY_PATTERNS
]


def has_profanity(text: str) -> tuple[bool, str | None]:
    """Return (found, matched_token). Token is None when clean."""
    for pattern in _PROFANITY_RE:
        m = pattern.search(text)
        if m:
            return True, m.group()
    return False, None


# ---------------------------------------------------------------------------
# Prompt injection / jailbreak patterns
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    # English — instruction override
    r"ignore\s+(all\s+)?(previous|prior|above|your)\s+instructions?",
    r"forget\s+(everything|all\s+previous|your\s+instructions?)",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions?",
    r"override\s+(your\s+)?(instructions?|guidelines?|rules?)",
    # English — persona swap
    r"you\s+are\s+now\s+(?!a\s+study)",
    r"act\s+as\s+(a|an)\s+(?!study\s+coach)",
    r"pretend\s+(to\s+be|you\s+are)\s+(?!a\s+study\s+coach)",
    r"roleplay\s+as",
    r"your\s+new\s+(role|persona|instructions?)\s+(is|are)",
    # English — known jailbreak tokens
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"\bjailbreak\b",
    r"prompt\s+injection",
    # English — raw system prompt injection markers
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"###\s*instruction",
    # Korean — instruction override
    r"이전\s*(지시|명령|설정|규칙).{0,10}(무시|잊어|지워)",
    r"(모든|기존)\s*(명령|지시).{0,10}(무시|잊어)",
    r"새로운\s*(지시|명령|역할|규칙)",
    r"지금부터\s+너는",
    # Korean — persona swap
    r"이제\s+너는\s+(?!공부\s*코치)",
    r"역할극",
    r"탈옥",
]

_INJECTION_RE = [
    re.compile(p, re.IGNORECASE | re.UNICODE) for p in _INJECTION_PATTERNS
]


def has_prompt_injection(text: str) -> tuple[bool, str | None]:
    """Return (found, matched_snippet)."""
    for pattern in _INJECTION_RE:
        m = pattern.search(text)
        if m:
            return True, m.group()
    return False, None


# ---------------------------------------------------------------------------
# Quick topic heuristic — only blocks obvious off-topic, defers the rest
# ---------------------------------------------------------------------------

_CLEARLY_OFF_TOPIC = frozenset([
    "게임", "유튜브", "틱톡", "인스타", "연예인", "아이돌",
    "축구", "농구", "야구", "포켓몬", "로블록스", "마인크래프트",
])

# Exact standalone greetings/acknowledgements acceptable in any touchpoint
_GREETINGS = frozenset([
    "안녕", "hi", "hello", "응", "네", "아니",
    "잠깐만", "고마워", "감사해", "ㅎㅎ", "ㅋㅋ", "ㅠㅠ",
])

TopicVerdict = str  # "on_topic" | "off_topic" | "unknown"


def quick_topic_verdict(text: str) -> TopicVerdict:
    """
    Cheap heuristic: 'on_topic', 'off_topic', or 'unknown'.
    'unknown' means defer to the LLM judge.

    Intentionally does NOT use study-keyword matching to return 'on_topic'
    because a message can contain a study word while being entirely off-topic.
    Positive topic decisions are left to the LLM.
    """
    stripped = text.strip().lower()

    # Single-token / very short responses pass without LLM check
    if len(stripped) <= 3:
        return "on_topic"

    # Exact standalone greeting → pass
    if stripped in _GREETINGS:
        return "on_topic"

    # Two or more clearly off-topic keywords → flag as off_topic
    off_count = sum(1 for kw in _CLEARLY_OFF_TOPIC if kw in stripped)
    if off_count >= 2:
        return "off_topic"

    return "unknown"
