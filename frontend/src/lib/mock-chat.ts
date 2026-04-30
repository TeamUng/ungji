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

export const demoStepLabels: Record<
  Exclude<DemoStepId, "exit" | "help" | "wrapup">,
  string
> = {
  home: "홈 추천",
  learning: "학습",
  complete: "완료",
};

export const demoCases: Record<DemoCaseId, DemoCase> = {
  "lower-korean": {
    studentId: "lower-high-lazy",
    studentName: "성준",
    label: "2학년 국어",
    touchpointByStep: {
      home: "tp1",
      learning: "tp4",
      help: "tp4",
      complete: "tp2",
      exit: "tp3",
      wrapup: "tp5",
    },
    tasks: [
      {
        subject: "국어",
        unit: "문단의 짜임 - 긴글 이해하기",
        problem_id: "lower_korean_paragraph_001",
      },
      {
        subject: "국어",
        unit: "문단의 짜임 - 중심 문장과 뒷받침 문장 찾기",
        problem_id: "lower_korean_paragraph_002",
      },
      {
        subject: "수학",
        unit: "한 자리 수 더하기",
        problem_id: "lower_math_addition_001",
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
    studentName: "아연",
    label: "6학년 수학",
    touchpointByStep: {
      home: "tp1",
      learning: "tp4",
      help: "tp4",
      complete: "tp2",
      exit: "tp3",
      wrapup: "tp5",
    },
    tasks: [
      {
        subject: "수학",
        unit: "비와 비율",
        problem_id: "math_ratio_saltwater_001",
      },
      {
        subject: "국어",
        unit: "정보와 표현 판단하기",
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
  options: {
    activeTaskIndex?: number;
    context?: Partial<ChatRequestContext>;
    threadIdSuffix?: string;
  } = {},
): ChatRequest {
  const demoCase = demoCases[caseId];
  const baseContext = contextForStep(demoCase, stepId, options.activeTaskIndex);
  const context = {
    ...baseContext,
    ...options.context,
  };

  return {
    thread_id: `tp-demo-${caseId}-${stepId}${
      options.threadIdSuffix ? `-${options.threadIdSuffix}` : ""
    }`,
    student_id: demoCase.studentId,
    use_case: getUseCaseForStep(stepId),
    current_touchpoint: demoCase.touchpointByStep[stepId],
    message: {
      type: messageType ?? (content ? "text" : "init"),
      content,
    },
    context,
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
          ? `${studentName}아, 오늘은 수학 비와 비율부터 차근차근 시작해보자. 조금 어려워 보여도 한 단계씩 보면 충분히 할 수 있어.`
          : `${studentName}아, 오늘은 잘하는 국어부터 시작해보자. 긴글 이해하기, 금세 풀 수 있어.`,
      },
      {
        type: "choices",
        items: [
          {
            id: "start_learning",
            label: isUpper ? "수학으로 이동하기" : "국어 시작하기",
          },
        ],
      },
    ];
  }

  if (stepId === "complete") {
    return [
      {
        type: "text",
        content: isUpper
          ? `${studentName}아, 어려운 수학을 끝까지 해낸 게 정말 좋아. 다음은 국어 정보와 표현 판단하기로 이어가 보자.`
          : "정답! 글의 흐름 잘 잡았어. 어려운 거 한 문제만 더 도전해볼까? 중심 문장과 뒷받침 문장 찾기야.",
      },
      {
        type: "choices",
        items: [
          {
            id: "continue_next_task",
            label: isUpper ? "국어로 이동하기" : "한 문제 더 도전",
          },
          { id: "end_today", label: "오늘은 여기까지" },
        ],
      },
    ];
  }

  if (stepId === "exit") {
    return [
      {
        type: "text",
        content: `${studentName}아, 한 문제만 더 풀면 오늘 끝이야. 마저 끝내고 편하게 쉬자.`,
      },
      {
        type: "choices",
        items: [
          { id: "continue_current_problem", label: "마저 하기" },
          { id: "ask_hint", label: "힌트 받고 풀기" },
        ],
      },
    ];
  }

  if (stepId === "wrapup") {
    return [
      {
        type: "text",
        content: isUpper
          ? `${studentName}아, 오늘 정말 잘 해냈어. 오늘 틀린 문제들 같이 복습하러 가자.`
          : `${studentName}아, 오늘 어려운 것까지 끝까지 한 게 멋졌어. 잘 마쳤으니 편히 쉬어. 안녕, 뽀롱~`,
      },
      {
        type: "choices",
        items: isUpper
          ? [{ id: "review_wrong_answers", label: "복습하러 가기" }]
          : [{ id: "finish_today", label: "마치기" }],
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
    const isUpper = contextCaseFromRequest(request) === "upper-math";
    return [
      {
        type: "text",
        content: isUpper
          ? "괜찮아. 어디에서 막혔는지 먼저 골라볼래?"
          : "어려웠구나. 어디가 헷갈렸는지 골라볼래?",
      },
      {
        type: "choices",
        items: isUpper
          ? [
              { id: "dont_understand_question", label: "문제가 이해가 안돼요" },
              { id: "confused_formula", label: "어떻게 푸는지 모르겠어요" },
              { id: "calculation_hard", label: "계산이 어려워요" },
            ]
          : [
              { id: "dont_understand_question", label: "문제가 무슨 말인지 모르겠어요" },
              { id: "dont_know_where", label: "어디를 봐야 할지 모르겠어요" },
              { id: "confused_answer", label: "그냥 답이 헷갈려요" },
            ],
      },
    ];
  }

  if (stepId === "help" && request.message.type === "choice") {
    return [
      {
        type: "text",
        content: contextCaseFromRequest(request) === "upper-math"
          ? "좋아, 먼저 문제에서 비교해야 하는 두 양을 찾아보자. 소금과 소금물 중 어떤 것이 전체 양일까?"
          : "좋아, 먼저 문장 하나만 같이 보자. 글에서 중심으로 말하는 낱말을 찾아볼까?",
      },
    ];
  }

  if (stepId === "help" && request.message.type === "text") {
    return [
      {
        type: "hint_card",
        steps: [
          { step: 1, content: "소금의 양과 소금물의 양을 먼저 나눠서 봐요." },
          { step: 2, content: "비율은 소금 ÷ 소금물로 생각해볼 수 있어요." },
        ],
      },
    ];
  }

  if (stepId === "exit") {
    return [
      {
        type: "text",
        content: "좋아, 딱 한 문제만 더 해보고 가자. 지금 화면에서 마저 이어가면 돼.",
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

  if (stepId === "wrapup") {
    const completedTaskRefs = firstTask ? demoCase.tasks.slice(0, activeTaskIndex + 1) : [];
    return {
      completed_task_refs: completedTaskRefs,
      current_task_ref: activeTask,
      today_tasks_completed: true,
      flow_event: "today_completed",
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
