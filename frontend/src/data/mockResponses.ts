import type { ChatRequest, ChatResponse, ResponseMessage } from "@/types/chat";
import type { StudentCase } from "@/types/learning";

function text(content: string): ResponseMessage {
  return { type: "text", content };
}

function choices(items: { id: string; label: string }[]): ResponseMessage {
  return { type: "choices", items };
}

function hintCard(steps: string[]): ResponseMessage {
  return {
    type: "hint_card",
    steps: steps.map((content, index) => ({ step: index + 1, content })),
  };
}

function imageCard(image_url: string, caption: string): ResponseMessage {
  return { type: "image_card", image_url, caption };
}

export function getMockMessages(
  request: ChatRequest,
  studentCase: StudentCase,
): ResponseMessage[] {
  const messageContent = request.message.content;

  if (request.current_touchpoint === "tp1") {
    if (studentCase.id === "case1") {
      return [
        text("하린아, 오늘은 짧은 글 하나만 해볼까? 그림을 보고 마음만 골라도 좋아."),
        choices([
          { id: "start:korean-short-reading", label: "그림 보고 마음 고르기" },
          { id: "start:math-counting", label: "수 세기 먼저 하기" },
        ]),
      ];
    }

    return [
      text("민준아, 오늘은 수학 비율부터 차근차근 해볼까요? 한 문제를 단계별로 같이 풀 수 있어요."),
      choices([
        { id: "start:math-ratio", label: "수학으로 이동하기" },
        { id: "start:korean-reading", label: "국어 먼저 하기" },
      ]),
    ];
  }

  if (request.current_touchpoint === "tp2") {
    return [
      text(`${studentCase.studentName}님, 방금 학습 하나를 끝냈어요. 흐름이 좋으니 다음 학습도 짧게 이어가 볼까요?`),
      choices([
        { id: `start:${studentCase.todayTasks[1]?.id ?? studentCase.recommendedTaskId}`, label: "다음 학습으로 이동하기" },
        { id: "finish-day", label: "오늘은 여기까지" },
      ]),
    ];
  }

  if (request.current_touchpoint === "tp3") {
    return [
      text("잠깐만요. 지금 나가도 괜찮지만, 이 문제에서 딱 한 부분만 같이 보고 끝낼 수 있어요."),
      choices([
        { id: "open-help", label: "코치랑 같이 보기" },
        { id: "finish-day", label: "오늘은 끝내기" },
      ]),
    ];
  }

  if (request.current_touchpoint === "tp4") {
    return getTp4Messages(messageContent, studentCase);
  }

  if (studentCase.wrongAnswerSummary.total === studentCase.wrongAnswerSummary.done) {
    return [
      text("오늘 틀린 문제까지 다 확인했어요. 이 정도면 정말 깔끔한 마무리예요."),
      choices([{ id: "finish-day", label: "마치기" }]),
    ];
  }

  return [
    text(
      `오늘 오답 ${studentCase.wrongAnswerSummary.total}개 중 ${studentCase.wrongAnswerSummary.done}개를 봤어요. 남은 문제를 아주 짧게만 확인하고 끝낼까요?`,
    ),
    choices([
      { id: "open-help", label: "오답 하나만 같이 보기" },
      { id: "finish-day", label: "오늘은 끝내기" },
    ]),
  ];
}

function getTp4Messages(content: string, studentCase: StudentCase): ResponseMessage[] {
  if (!content || content === "init") {
    if (studentCase.id === "case1") {
      return [
        text("어디가 어려워? 하나만 골라줘. 코치가 짧게 도와줄게."),
        choices([
          { id: "korean-too-long", label: "글이 너무 길어" },
          { id: "korean-situation", label: "무슨 상황인지 모르겠어" },
          { id: "korean-feeling", label: "주인공 마음을 모르겠어" },
          { id: "korean-tired", label: "그냥 하기 싫어" },
        ]),
      ];
    }

    return [
      text("어디가 막히는 것 같아요? 원인을 고르면 그 부분부터 같이 보겠습니다."),
      choices([
        { id: "math-meaning", label: "비율 뜻이 헷갈려요" },
        { id: "math-compare", label: "어떤 수끼리 비교할지 모르겠어요" },
        { id: "math-equation", label: "식을 어떻게 세우는지 모르겠어요" },
        { id: "math-calc", label: "계산하다가 틀렸어요" },
      ]),
    ];
  }

  if (content === "korean-too-long") {
    return [
      text("좋아. 긴 글로 보지 말고 한 줄씩만 보자."),
      hintCard([
        "토끼는 친구가 넘어진 걸 봤어요.",
        "토끼는 달려가서 손을 잡아 주었어요.",
        "도와주러 간 마음을 골라 보면 돼요.",
      ]),
    ];
  }

  if (content === "korean-situation") {
    return [
      imageCard("/assets/mock/story-scene.svg", "친구가 넘어지고, 토끼가 손을 잡아 주는 장면이에요."),
      text("그림에서는 누군가를 도와주는 장면이 보여. 그래서 토끼 마음은 걱정하고 도와주고 싶은 마음에 가까워."),
    ];
  }

  if (content === "korean-feeling") {
    return [
      text("선택지를 두 개로 줄여 볼게. 토끼가 친구를 보고 달려갔다면 어떤 마음일까?"),
      choices([
        { id: "korean-answer-worried", label: "걱정하는 마음" },
        { id: "korean-answer-angry", label: "화난 마음" },
      ]),
    ];
  }

  if (content === "korean-tired") {
    return [text("그럼 딱 한 문장만 읽고 끝내자. '친구가 넘어지자 달려갔다' 여기만 보면 답에 가까워져.")];
  }

  if (content === "math-meaning") {
    return [
      text("비율은 두 수를 비교하는 방법이에요. 지금 문제에서는 '하루에 29개'가 16번 반복되는지 보는 게 핵심이에요."),
      hintCard(["하루에 만든 수를 찾기", "며칠 동안인지 찾기", "같은 수가 반복되면 곱셈으로 나타내기"]),
    ];
  }

  if (content === "math-compare") {
    return [
      text("먼저 단위를 붙여 볼게요. 29는 '하루에 만든 개수', 16은 '날짜 수'예요."),
      hintCard(["하루에 29개", "16일 동안", "29개가 16번 반복"]),
    ];
  }

  if (content === "math-equation") {
    return [
      text("식을 세울 때는 반복되는 양을 앞에 두면 좋아요."),
      hintCard(["하루에 29개를 만들어요.", "그 일이 16일 동안 반복돼요.", "그래서 29 x 16으로 나타낼 수 있어요."]),
    ];
  }

  if (content === "math-calc") {
    return [
      text("계산은 두 줄로 나누면 실수가 줄어요. 29 x 10 = 290, 29 x 6 = 174, 둘을 더하면 464예요."),
      choices([{ id: "math-teach-back", label: "제가 다시 설명해볼게요" }]),
    ];
  }

  if (content === "math-teach-back") {
    return [text("좋아요. '29개가 16번 반복된다'는 말만 넣어서 설명하면 충분해요.")];
  }

  if (content.includes("걱정") || content.includes("29")) {
    return [text("맞아요. 방금 말한 방식으로 보면 문제의 핵심을 제대로 잡았어요.")];
  }

  return [text("좋아요. 그 생각에서 한 단계만 더 가 볼게요. 문제에서 반복되는 양이 무엇인지 먼저 찾아봅시다.")];
}

export function createMockResponse(
  request: ChatRequest,
  studentCase: StudentCase,
): ChatResponse {
  return {
    thread_id: request.thread_id,
    messages: getMockMessages(request, studentCase),
  };
}
