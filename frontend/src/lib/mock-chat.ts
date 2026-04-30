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
          ? `${studentName} 학생 환영해요~ 수학에서 자주 틀렸던 비와 비율 챕터부터 같이 해볼까요? 제가 옆에서 쉽게 알려드릴게요!`
          : "성준이가 잘하는 국어부터 시작해보자. 문장의 짜임 부분은 성준이라면 정답을 모두 맞힐 수 있을 것 같아!",
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
          ? "잘했어요! 어려웠던 비와 비율 문제를 끝까지 풀었네요. 다음은 아연 학생이 잘하는 국어를 해볼까요? 아마 다 맞을 수 있을 거에요!"
          : "너무 잘했어. 성준이라면 더 어려운 문제도 잘 할 것 같아. 같이 상위권 문제에 도전해보자",
      },
      {
        type: "choices",
        items: [
          {
            id: "continue_next_task",
            label: isUpper ? "국어 하러가기" : "심화 국어 도전하기",
          },
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
          ? `${studentName} 학생, 오늘 학습을 끝까지 완료한 걸 축하해요! 오늘 틀렸던 내용만 간단히 복습하고 끝내요!`
          : `${studentName}아 오늘 학습 끝까지 완료한 걸 축하해! 약속한대로 별 10개를 줄게! 내일 또 보자`,
      },
      {
        type: "choices",
        items: isUpper
          ? [{ id: "review_wrong_answers", label: "복습하러 가기" }]
          : [{ id: "finish_today", label: "완료하기" }],
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

    if (isUpperMathHelpRequest(request)) {
      return getUpperMathHelpInitMessages();
    }

    if (isLowerSecondKoreanHelpRequest(request)) {
      return getLowerSecondKoreanHelpInitMessages();
    }

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
    if (isUpperMathHelpRequest(request)) {
      const upperMathMessages = getUpperMathHelpChoiceMessages(
        request.message.content,
      );

      if (upperMathMessages) {
        return upperMathMessages;
      }
    }

    if (isLowerSecondKoreanHelpRequest(request)) {
      const lowerSecondMessages = getLowerSecondKoreanHelpChoiceMessages(
        request.message.content,
      );

      if (lowerSecondMessages) {
        return lowerSecondMessages;
      }
    }

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

export function getUpperMathHelpInitMessages(): ResponseMessage[] {
  return [
    {
      type: "text",
      content: "어느 부분이 어렵게 느껴지시나요?",
    },
    {
      type: "choices",
      items: [
        { id: "hard_understand_problem", label: "문제가 이해가 잘 안 돼요" },
        { id: "hard_solve_method", label: "어떻게 풀어야 할지 모르겠어요" },
        { id: "hard_calculation", label: "계산이 어려워요" },
      ],
    },
  ];
}

export function getUpperMathHelpChoiceMessages(
  content: string,
): ResponseMessage[] | null {
  if (isUpperMathOpeningChoice(content)) {
    return [
      {
        type: "text",
        content:
          "괜찮아요, 같이 천천히 살펴볼까요?\n\n구하려는 것은\n\"소금이 전체 소금물에서 얼마나 차지하는지\"에요!\n\n(가)\n소금 37g / 소금물 148g\n\n어떤 계산이 알맞을까요?",
      },
      {
        type: "choices",
        items: [
          { id: "ga_add", label: "37 + 148" },
          { id: "ga_subtract", label: "148 - 37" },
          { id: "ga_divide", label: "37 ÷ 148" },
        ],
      },
    ];
  }

  if (isUpperMathFirstFormulaChoice(content)) {
    return [
      {
        type: "text",
        content:
          "좋은 접근입니다\n\n37 ÷ 148\n\n여기서 148은 37의 몇 배인지 생각해볼까요?",
      },
      {
        type: "choices",
        items: [
          { id: "times_2", label: "2배" },
          { id: "times_3", label: "3배" },
          { id: "times_4", label: "4배" },
        ],
      },
    ];
  }

  if (isUpperMathMultipleChoice(content)) {
    return [
      {
        type: "text",
        content:
          "이번에는 (나)도 같은 방법으로 생각해볼까요?\n\n소금 76g / 소금물 380g\n\n어떤 식이 적절할까요?",
      },
      {
        type: "choices",
        items: [
          { id: "na_divide", label: "76 ÷ 380" },
          { id: "na_reverse_divide", label: "380 ÷ 76" },
          { id: "na_add", label: "76 + 380" },
        ],
      },
    ];
  }

  if (isUpperMathSecondFormulaChoice(content)) {
    return [
      {
        type: "text",
        content:
          "좋아요. 같은 방법으로 소금이 전체 소금물에서 차지하는 비율을 구하면 돼요.",
      },
    ];
  }

  return null;
}

function isUpperMathHelpRequest(request: ChatRequest) {
  return (
    contextCaseFromRequest(request) === "upper-math" &&
    request.context?.current_problem_id === "math_ratio_saltwater_001"
  );
}

function isUpperMathOpeningChoice(content: string) {
  return [
    "문제가 이해가 잘 안 돼요",
    "어떻게 풀어야 할지 모르겠어요",
    "계산이 어려워요",
  ].includes(content);
}

function isUpperMathFirstFormulaChoice(content: string) {
  return ["37 + 148", "148 - 37", "37 ÷ 148"].includes(content);
}

function isUpperMathMultipleChoice(content: string) {
  return ["2배", "3배", "4배"].includes(content);
}

function isUpperMathSecondFormulaChoice(content: string) {
  return ["76 ÷ 380", "380 ÷ 76", "76 + 380"].includes(content);
}

export function getLowerSecondKoreanHelpInitMessages(): ResponseMessage[] {
  return [
    {
      type: "text",
      content: "어려웠구나. 어디가 헷갈렸는지 골라볼래?",
    },
    {
      type: "choices",
      items: [
        { id: "unknown_main_sentence", label: "중심 문장이 뭔지 모르겠어" },
        { id: "unknown_support_sentence", label: "뒷받침 문장이 뭔지 모르겠어" },
        { id: "unknown_tidal_wave", label: "해일이 뭔지 모르겠어" },
      ],
    },
  ];
}

export function getLowerSecondKoreanHelpChoiceMessages(
  content: string,
): ResponseMessage[] | null {
  if (content === "중심 문장이 뭔지 모르겠어") {
    return [
      {
        type: "text",
        content:
          "중심 문장은 바다가 우리에게 도움이 되는 것이야\n\n그럼 뒷받침 문장에는 뭐가 있어야 할까?",
      },
      {
        type: "choices",
        items: [
          { id: "sea_good_points", label: "바다의 좋은 점" },
          { id: "sea_danger_points", label: "바다의 위험한 점" },
          { id: "sea_mountain_difference", label: "바다와 산의 차이점" },
        ],
      },
    ];
  }

  if (content === "바다의 좋은 점") {
    return [
      {
        type: "text",
        content:
          "맞아~\n그럼 바다의 좋은 점이 없는 문장을 선택지 중에서 골라볼까?",
      },
    ];
  }

  return null;
}

function isLowerSecondKoreanHelpRequest(request: ChatRequest) {
  return (
    contextCaseFromRequest(request) === "lower-korean" &&
    request.context?.current_problem_id === "lower_korean_paragraph_002"
  );
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
