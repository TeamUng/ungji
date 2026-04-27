"""
Fast, synchronous rule-based checks using regex and keyword matching.

These run before any LLM call to catch obvious violations cheaply (~0 ms).
All functions are pure and stateless — no I/O, no async.

Production note
---------------
The word lists below are intentionally minimal placeholders.
Replace / extend them with a curated moderation corpus maintained separately
(e.g. loaded from a config file or a private package).
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
# Quick topic heuristic (no LLM needed for obvious cases)
# ---------------------------------------------------------------------------

_STUDY_KEYWORDS = frozenset([
    "공부", "수학", "국어", "과학", "사회", "영어", "도덕", "체육",
    "문제", "답", "모르겠", "어려", "학습", "숙제", "시험", "점수",
    "개념", "설명", "도움", "힌트", "문장", "계산", "읽기", "쓰기",
    "풀기", "이해", "단원", "분수", "덧셈", "뺄셈", "곱셈", "나눗셈",
    "비율", "비례", "방정식", "도형", "넓이", "부피", "그래프",
    "주인공", "이야기", "독서", "받아쓰기", "일기", "소수", "배수",
])

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
    """
    stripped = text.strip().lower()

    # Single-token / very short responses (≤3 chars) pass without LLM check.
    # Threshold is 3 because Korean chars each count as 1 in len(), so
    # "유튜브 보고 싶다" (9 chars) must NOT be short-circuited here.
    if len(stripped) <= 3:
        return "on_topic"

    # Exact greeting strings — only match if the whole message is a greeting
    if stripped in _GREETINGS:
        return "on_topic"

    if any(kw in stripped for kw in _STUDY_KEYWORDS):
        return "on_topic"

    off_count = sum(1 for kw in _CLEARLY_OFF_TOPIC if kw in stripped)
    if off_count >= 2:
        return "off_topic"

    return "unknown"
