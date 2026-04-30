import type {
  ChatAdapter,
  ChatRequest,
  ChatRequestContext,
  DemoCaseId,
  DemoStepId,
  IncomingMessageType,
  ResponseMessage,
  TaskRef,
  Touchpoint,
  UseCase,
} from "@/types/chat";

type DemoCase = {
  studentId: string;
  studentName: string;
  label: string;
  touchpointByStep: Record<DemoStepId, Touchpoint>;
  tasks: TaskRef[];
};

export const demoStepLabels: Record<Exclude<DemoStepId, "exit" | "help">, string> = {
  home: "홈 추천",
  learning: "학습",
  complete: "완료",
};

export const demoCases: Record<DemoCaseId, DemoCase> = {
  "lower-korean": {
    studentId: "lower-high-lazy",
    studentName: "도윤",
    label: "2학년 국어",
    touchpointByStep: {
      home: "tp1",
      learning: "tp4",
      help: "tp4",
      complete: "tp2",
      exit: "tp3",
    },
    tasks: [
      {
        subject: "국어",
        unit: "받침이 있는 낱말 읽기",
        problem_id: "lower_korean_reading_001",
      },
      {
        subject: "수학",
        unit: "한 자리 수 더하기",
        problem_id: "lower_math_addition_001",
      },
      {
        subject: "통합",
        unit: "봄 관찰하기",
        problem_id: "lower_integrated_season_001",
      },
      {
        subject: "영어",
        unit: "알파벳 익히기",
        problem_id: "lower_english_alphabet_001",
      },
    ],
  },
  "upper-math": {
    studentId: "upper-low-diligent",
    studentName: "서연",
    label: "6학년 수학",
    touchpointByStep: {
      home: "tp1",
      learning: "tp4",
      help: "tp4",
      complete: "tp2",
      exit: "tp3",
    },
    tasks: [
      {
        subject: "수학",
        unit: "비율과 비례식",
        problem_id: "math_ratio_saltwater_001",
      },
      {
        subject: "국어",
        unit: "주장과 근거 파악하기",
        problem_id: "upper_korean_argument_001",
      },
      {
        subject: "과학",
        unit: "생태계와 환경",
        problem_id: "upper_science_ecosystem_001",
      },
      {
        subject: "사회",
        unit: "세계 여러 나라의 환경",
        problem_id: "upper_social_environment_001",
      },
    ],
  },
};

export const demoStudentOptions = [
  {
    caseId: "lower-korean" as const,
    studentId: demoCases["lower-korean"].studentId,
    label: `${demoCases["lower-korean"].studentName} · ${demoCases["lower-korean"].label}`,
  },
  {
    caseId: "upper-math" as const,
    studentId: demoCases["upper-math"].studentId,
    label: `${demoCases["upper-math"].studentName} · ${demoCases["upper-math"].label}`,
  },
];

export function makeChatRequest(
  caseId: DemoCaseId,
  stepId: DemoStepId,
  content = "",
  messageType?: IncomingMessageType,
  options: { activeTaskIndex?: number } = {},
): ChatRequest {
  const demoCase = demoCases[caseId];

  return {
    thread_id: `tp-demo-${caseId}-${stepId}`,
    student_id: demoCase.studentId,
    use_case: getUseCaseForStep(stepId),
    current_touchpoint: demoCase.touchpointByStep[stepId],
    message: {
      type: messageType ?? (content ? "text" : "init"),
      content,
    },
    context: contextForStep(demoCase, stepId, options.activeTaskIndex),
  };
}

export function getStepMessages(
  caseId: DemoCaseId,
  stepId: DemoStepId,
): ResponseMessage[] {
  const isUpper = caseId === "upper-math";
  const studentName = demoCases[caseId].studentName;

  if (stepId === "home") {
    return [
      {
        type: "text",
        content: isUpper
          ? `${studentName}아, 오늘은 비율과 비례식부터 차근차근 시작해볼까?`
          : `${studentName}아, 뽀롱~ 국어 한 문제부터 가볍게 시작해볼까?`,
      },
      {
        type: "choices",
        items: [{ id: "start_learning", label: "학습시작" }],
      },
    ];
  }

  if (stepId === "complete") {
    return [
      {
        type: "text",
        content: isUpper
          ? "좋아요. 방금 단원은 마쳤고, 다음은 국어 주장과 근거를 이어가면 좋아요."
          : "잘했어! 이제 수학 한 자리 수 더하기를 짧게 이어가볼까?",
      },
      {
        type: "choices",
        items: [
          { id: "continue_next_task", label: "다음 학습 하기" },
          { id: "end_today", label: "오늘은 여기까지" },
        ],
      },
    ];
  }

  if (stepId === "exit") {
    return [
      {
        type: "text",
        content: "벌써 나가고 싶구나. 그럼 딱 한 문제만 더 풀어볼까?",
      },
      {
        type: "choices",
        items: [
          { id: "continue_current_problem", label: "한 문제만 더 풀기" },
          { id: "ask_hint", label: "힌트 받고 풀기" },
        ],
      },
    ];
  }

  return [];
}

export const mockChatAdapter: ChatAdapter = async function* (
  request,
  context,
) {
  await wait(120);

  const stepMessages = getMockConversationMessages(request, context.stepId);
  for (const message of stepMessages) {
    yield message;
    await wait(80);
  }
};

function getMockConversationMessages(
  request: ChatRequest,
  stepId: DemoStepId,
): ResponseMessage[] {
  if (stepId === "help" && request.message.type === "init") {
    return [
      {
        type: "choices",
        items: [
          { id: "dont_understand_question", label: "문제가 무슨 말인지 모르겠어요" },
          { id: "confused_formula", label: "식을 어떻게 세울지 모르겠어요" },
          { id: "calculation_hard", label: "계산이 어려워요" },
        ],
      },
    ];
  }

  if (stepId === "help" && request.message.type === "choice") {
    return [
      {
        type: "text",
        content: "좋아, 먼저 문제에서 묻는 것을 네 말로 한 번 말해볼래?",
      },
    ];
  }

  if (stepId === "help" && request.message.type === "text") {
    return [
      {
        type: "hint_card",
        steps: [
          { step: 1, content: "문제에서 기준이 되는 양을 찾아봐요." },
          { step: 2, content: "같은 비율이 되도록 함께 변하는 양을 확인해요." },
        ],
      },
    ];
  }

  if (stepId === "exit") {
    return [
      {
        type: "text",
        content: "좋아, 딱 한 문제만 더 해보고 가자. 지금 문제에서 제일 작은 한 걸음부터 보자.",
      },
    ];
  }

  return getStepMessages(contextCaseFromRequest(request), stepId);
}

function contextForStep(
  demoCase: DemoCase,
  stepId: DemoStepId,
  activeTaskIndex = 0,
): ChatRequestContext | undefined {
  const firstTask = demoCase.tasks[0];
  const activeTask = demoCase.tasks[activeTaskIndex] ?? firstTask;
  const nextTask = demoCase.tasks[1] ?? firstTask;

  if (stepId === "complete") {
    return {
      completed_task_refs: [firstTask],
      current_task_ref: nextTask,
    };
  }

  if (stepId === "exit") {
    return {
      current_task_ref: activeTask,
      current_task_remaining_count: 2,
      current_problem_id: activeTask.problem_id,
    };
  }

  if (stepId === "help") {
    return {
      current_task_ref: activeTask,
      current_problem_id: activeTask.problem_id,
    };
  }

  return undefined;
}

function getUseCaseForStep(stepId: DemoStepId): UseCase {
  return stepId === "help" ? "learning" : "talk";
}

function contextCaseFromRequest(request: ChatRequest): DemoCaseId {
  return request.student_id === demoCases["upper-math"].studentId
    ? "upper-math"
    : "lower-korean";
}

function wait(ms: number) {
  return new Promise((resolve) => globalThis.setTimeout(resolve, ms));
}
