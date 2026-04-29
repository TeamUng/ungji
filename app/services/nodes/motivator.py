from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.enums import Touchpoint, UseCase
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatState, Task
from app.services.nodes.common import make_chat_response, make_text
from app.services.prompts.agents import MOTIVATOR_ROLE, build_system_prompt

logger = get_logger(__name__)

_HISTORY_WINDOW = 20
_BOOK_CLUB_LABEL = "Book Club"
_META_OUTPUT_MARKERS = (
    "내부 참고",
    "선택 이유",
    "추천 이유",
    "응답 예정",
    "학생의 반응",
    "실제 화면 구성",
    "현재 문제 유형을 가정",
    "ESSENTIAL",
    "send_text",
    "예를 들어",
    "예시:",
    "교과서",
    "페이지",
    "퀴즈",
    "미션",
    "문제 선택 이유",
)


def _task_key(task: Task | dict) -> tuple[str, str]:
    return str(task.get("subject", "")), str(task.get("unit", ""))


def _remaining_tasks(today_tasks: list[Task] | list[dict], completed_tasks: list[Task] | list[dict]) -> list:
    completed_keys = {_task_key(task) for task in completed_tasks}
    return [task for task in today_tasks if _task_key(task) not in completed_keys]


def _task_lines(tasks: list[Task] | list[dict]) -> str:
    if not tasks:
        return "없어."

    lines: list[str] = []
    for index, task in enumerate(tasks, 1):
        score_info = (
            f", 예상 점수 {task['ai_predicted_score']}점"
            if task.get("ai_predicted_score") is not None
            else ""
        )
        lines.append(
            f"{index}. {task.get('subject', '')} - {task.get('unit', '')} "
            f"(난이도 {task.get('difficulty', '')}, {task.get('problem_count', '')}문제, "
            f"{task.get('estimated_time', '')}분{score_info})"
        )
    return "\n".join(lines)


def _unit_boundary_request(tasks: list[Task] | list[dict], *, allow_close: bool = False) -> str:
    if not tasks:
        return (
            f"오늘 남은 단원은 없어. 새 공부를 만들지 말고 앱의 {_BOOK_CLUB_LABEL}을 알려줘. "
            "새 문제, 예시, 퀴즈, 교과서 페이지, 복습문제, 숙제는 만들지 말아줘."
        )

    close_rule = "내가 오늘은 끝내고 싶어하면 따뜻하게 마무리해줘. " if allow_close else ""
    return (
        f"{close_rule}"
        "위 목록에 실제로 있는 단원 중 하나만 골라줘. "
        "새 문제, 예시, 퀴즈, 교과서 페이지, 복습문제, 숙제는 만들지 말아줘. "
        "단원 목록 전체를 다시 선택지처럼 나열하지 말고, 지금 시작할 하나만 추천해줘."
    )


def _current_task_action_request() -> str:
    return (
        "새 문제, 예시, 퀴즈, 교과서 페이지, 복습문제, 숙제는 만들지 말아줘. "
        "구체적인 낱말, 문장, 숫자식, 보기, 페이지 번호를 새로 말하지 말아줘. "
        "지금 화면에 이미 있는 첫 줄, 첫 보기, 첫 문제처럼 위치만 가리켜줘."
    )


def _latest_student_message(chat_history) -> str:
    for message in reversed(chat_history):
        if message.__class__.__name__ == "HumanMessage":
            content = getattr(message, "content", "")
            if content:
                return str(content)
    return ""


def _student_call_name(name: str) -> str:
    if not name:
        return "친구야"
    last = name[-1]
    code = ord(last) - 0xAC00
    if 0 <= code <= 11171 and code % 28:
        return f"{name}아"
    return f"{name}야"


def _needs_motivator_repair(content: str, touchpoint: Touchpoint | None) -> bool:
    if any(marker in content for marker in _META_OUTPUT_MARKERS):
        return True
    if touchpoint == Touchpoint.TP3:
        return any(marker in content for marker in ("작은 그림", "숫자", "낱말", "문장", "문제 첫", "첫 문제"))
    if touchpoint in (Touchpoint.TP1, Touchpoint.TP2, Touchpoint.TP5):
        return any(marker in content for marker in ("첫 문제", "문제 1개", "개념", "풀이", "힌트"))
    return False


def _repair_motivator_response(state: ChatState, llm, messages, content: str) -> str:
    profile = state["student_profile"]
    touchpoint = state.get("current_touchpoint")
    call_name = _student_call_name(str(profile.get("name", "")))
    repair_prompt = (
        "방금 답변은 아이에게 그대로 보낼 수 없어. "
        "메타 설명이나 새 문제/예시/퀴즈/교과서 페이지/풀이가 섞였을 수 있어.\n"
        f"학생을 부를 때는 반드시 '{call_name}'라고 불러.\n"
        "다시 작성해줘. 아이에게 보낼 말만 출력하고, 괄호 속 내부 설명을 쓰지 마.\n"
        "Motivator는 수업 내용을 가르치지 말고, 제공된 단원 중 하나를 추천하거나 짧게 응원만 해야 해.\n"
    )
    if touchpoint == Touchpoint.TP3:
        repair_prompt += (
            "TP3에서는 구체적인 낱말, 문장, 숫자식, 그림을 만들지 말고 "
            "'지금 화면의 첫 줄만 보자'처럼 화면 위치만 가리켜.\n"
        )
    repair_prompt += f"\n수정해야 할 원문:\n{content}"
    repaired = llm.invoke([*messages, HumanMessage(content=repair_prompt)])
    return str(getattr(repaired, "content", "") or content)


def motivator(state: ChatState) -> ChatResponse:
    """Handle TP1, TP2, TP3, TP5, and non-TP4 free chat turns."""
    from app.clients.llm import motivator_llm as llm

    grade_group = state["grade_group"]
    segment = state["segment"]
    touchpoint = state["current_touchpoint"]
    chat_history = state.get("chat_history", [])

    system_prompt = build_system_prompt(grade_group, segment, MOTIVATOR_ROLE)
    situation = _get_situation(state)
    recent = chat_history[-_HISTORY_WINDOW:] if len(chat_history) > _HISTORY_WINDOW else chat_history

    messages = [SystemMessage(content=system_prompt)]
    messages += list(recent)
    if situation:
        messages.append(HumanMessage(content=situation))

    logger.info(
        "motivator node invoked",
        extra={
            "student_id": state["student_id"],
            "touchpoint": touchpoint.value if touchpoint else "chat",
            "segment": segment.value,
        },
    )

    response = llm.invoke(messages)
    content = str(getattr(response, "content", ""))
    if _needs_motivator_repair(content, touchpoint):
        logger.warning(
            "motivator response repaired before delivery",
            extra={
                "student_id": state["student_id"],
                "touchpoint": touchpoint.value if touchpoint else "chat",
            },
        )
        content = _repair_motivator_response(state, llm, messages, content)

    logger.info("motivator node completed", extra={"student_id": state["student_id"]})

    return make_chat_response(state["thread_id"], [make_text(content)])


def _get_situation(state: ChatState) -> str:
    touchpoint = state.get("current_touchpoint")

    if state["use_case"] == UseCase.CHAT:
        return _situation_chat(state)

    if touchpoint == Touchpoint.TP1:
        return _situation_tp1(state)
    if touchpoint == Touchpoint.TP2:
        return _situation_tp2(state)
    if touchpoint == Touchpoint.TP3:
        return _situation_tp3(state)
    if touchpoint == Touchpoint.TP5:
        return _situation_tp5(state)
    return ""


def _situation_chat(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    touchpoint = state.get("current_touchpoint")
    latest = _latest_student_message(state.get("chat_history", []))
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining = _remaining_tasks(today_tasks, completed_tasks)
    active_tasks = remaining if completed_tasks else today_tasks

    if touchpoint == Touchpoint.TP3:
        current_task = state.get("current_task")
        task_line = _task_lines([current_task] if current_task else [])
        return (
            f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
            f"방금 이렇게 말했어: \"{latest}\"\n"
            f"지금 화면의 현재 단원:\n{task_line}\n\n"
            "내 말에 이어서 바로 대답해줘. "
            "내가 조금 더 해보겠다고 하면 새 학습 내용을 만들지 말고, "
            "현재 화면 안에서 할 수 있는 아주 작은 행동 하나만 말해줘. "
            f"{_current_task_action_request()}"
        )

    if touchpoint == Touchpoint.TP5 and "여기까지" in latest:
        return (
            f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
            f"방금 이렇게 말했어: \"{latest}\"\n\n"
            "오늘은 끝내겠다는 뜻이야. 새 공부나 내일 할 문제를 만들지 말고 따뜻하게 마무리해줘. "
            "제공된 단원 이름을 새 과제처럼 말하지 말고, 짧게 칭찬하고 쉬라고 말해줘."
        )

    return (
        f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
        f"방금 이렇게 말했어: \"{latest}\"\n"
        f"내 홈 화면에서 지금 말할 수 있는 단원:\n{_task_lines(active_tasks)}\n\n"
        "내 말에 이어서 바로 대답해줘. "
        "내가 추천한 단원을 해보겠다고 하면 짧게 응원만 하고, 수업 설명이나 문제 풀이를 시작하지 마. "
        "추천이 필요하면 위 단원 중 하나만 말해줘. "
        f"{_unit_boundary_request(active_tasks)}"
    )


def _situation_tp1(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    today_tasks = state["today_tasks"]
    pattern = state["learning_pattern"]

    habits = [
        label
        for label, enabled in {
            "건너뛰는 습관": pattern.get("skipping_habit"),
            "찍는 습관": pattern.get("guessing_habit"),
            "대충 푸는 습관": pattern.get("careless_habit"),
        }.items()
        if enabled
    ]
    habit_line = f"내 학습 습관 참고: {', '.join(habits)}\n" if habits else ""

    return (
        f"안녕, 나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. 지금 앱 홈 화면을 열었어.\n"
        f"내 최근 평균 점수는 {profile['recent_avg_score']}점이고, "
        f"좋아하는 과목은 {profile['preferred_subject']}, 잘하는 과목은 {profile['strong_subject']}야.\n"
        f"{habit_line}"
        "오늘 홈 화면에는 4개 단원이 보여:\n"
        f"{_task_lines(today_tasks)}\n\n"
        "이 중에서 지금 바로 시작할 추천 단원 하나만 알려줘. "
        f"{_unit_boundary_request(today_tasks)}"
    )


def _situation_tp2(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining = _remaining_tasks(today_tasks, completed_tasks)

    if remaining:
        return (
            f"안녕, 나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
            "방금 아래 단원을 끝냈어:\n"
            f"{_task_lines(completed_tasks)}\n\n"
            f"아직 남은 단원은 {len(remaining)}개야:\n"
            f"{_task_lines(remaining)}\n\n"
            "다음에 무엇을 하면 좋을지 남은 단원 중 하나만 추천해줘. "
            f"{_unit_boundary_request(remaining)}"
        )

    return (
        f"안녕, 나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. "
        f"오늘 할 단원 {len(today_tasks)}개를 모두 끝냈어.\n"
        f"완료한 단원:\n{_task_lines(completed_tasks)}\n\n"
        f"남은 단원이 없으니 새 공부를 만들지 말고 {_BOOK_CLUB_LABEL}을 알려줘. "
        f"{_unit_boundary_request(remaining)}"
    )


def _situation_tp3(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    current_task = state.get("current_task")
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining_count = len(_remaining_tasks(today_tasks, completed_tasks))

    if current_task:
        task_info = (
            f"지금 하고 있는 단원은 {current_task['subject']} - {current_task['unit']}이야 "
            f"(난이도 {current_task['difficulty']})."
        )
        current_units = [current_task]
    else:
        task_info = "지금 하고 있는 단원 정보는 없어."
        current_units = []

    return (
        f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. {task_info}\n"
        f"아직 남은 단원 수는 {remaining_count}개야.\n\n"
        "지금 나가고 싶어졌어. 강요하지 말고 공감해줘. "
        "그래도 계속할 수 있게 현재 단원 안에서 할 수 있는 아주 작은 행동 하나만 말해줘. "
        f"{_current_task_action_request()}"
    )


def _situation_tp5(state: ChatState) -> str:
    profile = state["student_profile"]
    call_name = _student_call_name(str(profile.get("name", "")))
    today_tasks = state["today_tasks"]
    completed_tasks = state["completed_tasks"]
    remaining = _remaining_tasks(today_tasks, completed_tasks)
    wrong_summary = _build_wrong_answer_summary(state)

    if remaining:
        next_request = (
            "홈 화면으로 돌아온 상태라면 남은 단원 중 추천 단원 하나만 알려줘. "
            "내가 오늘은 끝내겠다고 말하면 따뜻하게 마무리해줘. "
            f"{_unit_boundary_request(remaining, allow_close=True)}"
        )
    else:
        next_request = (
            f"남은 단원이 없으니 새 공부를 만들지 말고 {_BOOK_CLUB_LABEL}을 알려줘. "
            f"{_unit_boundary_request(remaining, allow_close=True)}"
        )

    return (
        f"나는 {profile['name']}이고 {profile['grade']}학년이야. 나를 부를 때는 '{call_name}'라고 불러줘. 오늘 학습을 마치려 해.\n"
        f"완료한 단원 ({len(completed_tasks)}/{len(today_tasks)}개):\n"
        f"{_task_lines(completed_tasks)}\n\n"
        f"남은 단원:\n{_task_lines(remaining)}\n"
        f"오답 상황: {wrong_summary}\n"
        f"오늘 평균 점수: {state['today_score']}점\n\n"
        f"{next_request}"
    )


def _build_wrong_answer_summary(state: ChatState) -> str:
    has_wrong = state["has_wrong_answers"]
    wrong_done_today = state["wrong_content_done_today"]
    pattern = state["learning_pattern"]
    wrong_total = pattern.get("wrong_content_total", 0)
    wrong_done = pattern.get("wrong_content_done", 0)

    if not has_wrong:
        return "오늘 틀린 문제는 없어."
    if wrong_done_today:
        return f"오늘 오답 {wrong_total}개를 모두 복습했어."
    remaining = max(wrong_total - wrong_done, 0)
    return f"오답 {wrong_total}개 중 {remaining}개가 아직 남아 있어."
