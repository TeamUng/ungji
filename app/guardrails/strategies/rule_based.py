"""
Fast, synchronous rule-based checks using regex and keyword matching.

These run before any LLM call to catch obvious violations cheaply (~0 ms).
All functions are pure and stateless — no I/O, no async.

Design note — topic verdict
---------------------------
quick_topic_verdict uses a TF-IDF cosine-similarity classifier fit on curated
off-topic example sentences.  A message is flagged "off_topic" only when its
similarity to off-topic examples exceeds _OFF_TOPIC_THRESHOLD AND no study
signal is present (conflict → "unknown").  This is more robust than keyword
counting but preserves the core invariant: positive "on_topic" decisions are
only made for greetings/short affirmations — everything else defers to the LLM.
"""

from __future__ import annotations

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Profanity / inappropriate content
# ---------------------------------------------------------------------------

_PROFANITY_PATTERNS = [
    r"시발|씨발|ㅅㅂ",
    r"병신|ㅂㅅ",
    r"개새끼|개색끼",
    r"존나|졸라",
    r"미친놈|미친년",
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
    r"ignore\s+(all\s+)?(previous|prior|above|your)\s+instructions?",
    r"forget\s+(everything|all\s+previous|your\s+instructions?)",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions?",
    r"override\s+(your\s+)?(instructions?|guidelines?|rules?)",
    r"you\s+are\s+now\s+(?!a\s+study)",
    r"act\s+as\s+(a|an)\s+(unrestricted|unfiltered|uncensored|jailbroken|evil|free)",
    r"pretend\s+(to\s+be|you\s+are)\s+(?!a\s+study\s+coach)",
    r"roleplay\s+as",
    r"your\s+new\s+(role|persona|instructions?)\s+(is|are)",
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"\bjailbreak\b",
    r"prompt\s+injection",
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"###\s*instruction",
    r"이전\s*(지시|명령|설정|규칙).{0,10}(무시|잊어|지워)",
    r"(모든|기존)\s*(명령|지시).{0,10}(무시|잊어)",
    r"새로운\s*(지시|명령|역할|규칙)",
    r"지금부터\s+너는",
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
# Quick topic classifier — only blocks obvious off-topic, defers the rest
# ---------------------------------------------------------------------------

_GREETINGS = frozenset([
    "안녕", "hi", "hello", "응", "네", "아니",
    "잠깐만", "고마워", "감사해", "ㅎㅎ", "ㅋㅋ", "ㅠㅠ",
])

# Study-domain signals used to detect conflicts with off-topic scores.
# A message that matches off-topic examples but also contains a study signal
# is ambiguous — defer to the LLM rather than blocking.
_STUDY_SIGNALS = frozenset([
    "수학", "과학", "국어", "영어", "사회", "역사", "도덕",
    "숙제", "공부", "문제", "시험", "퀴즈", "점수",
    "분수", "곱셈", "나눗셈", "덧셈", "뺄셈", "방정식",
    "단어", "문장", "독서", "일기", "작문",
    "실험", "원소", "식물", "동물", "지구",
    "힌트", "풀이", "정답", "오답", "이해",
])

# Curated off-topic sentences the classifier is fitted on (no training data
# needed — we fit a TF-IDF vectorizer on these at module load time, ~1 ms).
_OFF_TOPIC_EXAMPLES = [
    # streaming / video
    "유튜브 영상 추천해줘",
    "유튜브 보고 싶어",
    "틱톡 재밌는 영상 알려줘",
    "틱톡 챌린지 알려줘",
    "넷플릭스 뭐 볼까",
    # games
    "게임 공략 알려줘",
    "로블록스 어떻게 해",
    "마인크래프트 집 만드는 법",
    "포켓몬 잡는 방법",
    "게임 하고 싶어",
    "게임 추천해줘",
    # celebrities / idols
    "아이돌 노래 추천해줘",
    "연예인 나이 알려줘",
    "인기 가수 누구야",
    "BTS 새 앨범 나왔어",
    # sports
    "축구 경기 결과 알려줘",
    "농구 규칙 알려줘",
    "야구 중계 어디서 봐",
    # social media
    "인스타 팔로워 늘리는 법",
    "인스타그램 스토리 올리는 법",
]

# Similarity threshold above which a message is considered off-topic.
# Tuned so that single-keyword ambiguous messages fall below the threshold.
_OFF_TOPIC_THRESHOLD = 0.28

_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
_off_topic_matrix = _vectorizer.fit_transform(_OFF_TOPIC_EXAMPLES)

TopicVerdict = str  # "on_topic" | "off_topic" | "unknown"


def quick_topic_verdict(text: str) -> TopicVerdict:
    """
    Returns 'on_topic', 'off_topic', or 'unknown'.
    'unknown' means defer to the LLM judge.

    Intentionally does NOT return 'on_topic' for study keywords — a message
    can contain a study word while being entirely off-topic.  Positive topic
    decisions are left to the LLM.
    """
    stripped = text.strip().lower()

    # Exact standalone greeting / short affirmation → on_topic
    if stripped in _GREETINGS:
        return "on_topic"

    # Classifier: cosine similarity to off-topic examples
    vec = _vectorizer.transform([stripped])
    scores = cosine_similarity(vec, _off_topic_matrix)[0]
    off_topic_score: float = float(np.max(scores))

    if off_topic_score >= _OFF_TOPIC_THRESHOLD:
        # If the message also contains a study signal it is ambiguous → unknown
        if any(kw in stripped for kw in _STUDY_SIGNALS):
            return "unknown"
        return "off_topic"

    return "unknown"
