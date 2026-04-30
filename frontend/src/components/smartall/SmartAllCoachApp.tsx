"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { InteractionZone } from "@/components/chatbot/InteractionZone";
import { InteractionZoneProvider } from "@/components/chatbot/InteractionZoneProvider";
import type { InteractionZoneId } from "@/components/chatbot/chatbotSuggestions";
import { PorongCoachPanel } from "@/components/porong/PorongCoachPanel";
import { PorongOverlay } from "@/components/porong/PorongOverlay";
import type {
  PorongBubbleAction,
  PorongOverlayState,
} from "@/components/porong/porongTypes";
import { liveChatAdapter } from "@/lib/live-chat";
import {
  demoCases,
  demoStepLabels,
  demoStudentOptions,
  getLowerSecondKoreanHelpChoiceMessages,
  getLowerSecondKoreanHelpInitMessages,
  getStepMessages,
  makeChatRequest,
  mockChatAdapter,
} from "@/lib/mock-chat";
import type {
  ChatAdapter,
  ChatRequestContext,
  ChoiceSelection,
  ChatTurn,
  DemoCaseId,
  DemoRunMode,
  DemoStepId,
  IncomingMessageType,
  ResponseMessage,
  TaskRef,
} from "@/types/chat";

type SmartAllCoachAppProps = {
  showDemoControls?: boolean;
  initialCaseId?: DemoCaseId;
  demoMode?: DemoRunMode;
  chatAdapter?: ChatAdapter;
};

const orderedSteps: (keyof typeof demoStepLabels)[] = [
  "home",
  "learning",
  "complete",
];

const subjectsByCase: Record<DemoCaseId, string[]> = {
  "lower-korean": ["국어", "심화 국어", "수학", "영어"],
  "upper-math": ["수학", "국어", "과학", "사회"],
};

const THINKING_BUBBLE_TEXT = "뽀롱~ 생각 중이야...";

const defaultChatAdapter =
  process.env.NEXT_PUBLIC_UNGJI_CHAT_MODE === "live"
    ? liveChatAdapter
    : mockChatAdapter;

type DemoFlowStageId =
  | "home"
  | "learning"
  | "lower_first_correct"
  | "lower_second_exit"
  | "lower_second_wrong"
  | "lower_second_corrected"
  | "lower_final"
  | "upper_math_complete"
  | "upper_today_done"
  | "upper_review";

type AnswerResult = "correct" | "incorrect" | "corrected" | null;

function getFlowContext(
  caseId: DemoCaseId,
  stageId: DemoFlowStageId,
): Partial<ChatRequestContext> {
  if (stageId === "home") {
    return { flow_event: "home_entered" };
  }

  if (stageId === "lower_first_correct") {
    return {
      flow_event: "answer_submitted",
      answer_result: "correct",
      today_tasks_completed: false,
    };
  }

  if (stageId === "lower_second_exit") {
    return {
      flow_event: "exit_attempt",
      current_task_remaining_count: 1,
      today_tasks_completed: false,
    };
  }

  if (stageId === "lower_second_wrong") {
    return {
      flow_event: "porong_help_opened",
      answer_result: "incorrect",
      today_tasks_completed: false,
    };
  }

  if (stageId === "lower_second_corrected") {
    return {
      flow_event: "answer_submitted",
      answer_result: "correct",
      today_tasks_completed: false,
    };
  }

  if (stageId === "lower_final") {
    return {
      flow_event: "finish_clicked",
      answer_result: "incorrect",
      today_tasks_completed: true,
    };
  }

  if (stageId === "upper_math_complete") {
    return {
      flow_event: "task_completed",
      answer_result: "correct",
      today_tasks_completed: false,
    };
  }

  if (stageId === "upper_today_done") {
    return {
      flow_event: "today_completed",
      today_tasks_completed: true,
    };
  }

  if (stageId === "upper_review") {
    return {
      flow_event: "review_clicked",
      today_tasks_completed: true,
    };
  }

  return {
    flow_event: caseId === "upper-math" ? "porong_help_opened" : "home_entered",
  };
}

function getFallbackBubbleMessages(
  caseId: DemoCaseId,
  stepId: DemoStepId,
  stageId: DemoFlowStageId,
): ResponseMessage[] {
  if (stageId === "lower_final") {
    return [
      {
        type: "text",
        content:
          "성준아 오늘 학습 끝까지 완료한 걸 축하해! 약속한대로 별 10개를 줄게! 내일 또 보자",
      },
      {
        type: "choices",
        items: [{ id: "finish_today", label: "완료하기" }],
      },
    ];
  }

  return getStepMessages(caseId, stepId);
}

function getFallbackChatMessages(
  caseId: DemoCaseId,
  targetStepId: DemoStepId,
  messageType?: IncomingMessageType,
  content = "",
  activeTaskIndex = 0,
): ResponseMessage[] {
  const isUpper = caseId === "upper-math";
  const isLowerSecondKoreanHelp =
    caseId === "lower-korean" && activeTaskIndex === 1;

  if (targetStepId !== "help") {
    return getStepMessages(caseId, targetStepId);
  }

  if (isLowerSecondKoreanHelp) {
    if (messageType === "choice") {
      const lowerSecondMessages = getLowerSecondKoreanHelpChoiceMessages(content);

      if (lowerSecondMessages) {
        return lowerSecondMessages;
      }
    } else {
      return getLowerSecondKoreanHelpInitMessages();
    }
  }

  if (messageType === "choice") {
    return [
      {
        type: "text",
        content: isUpper
          ? "좋아, 먼저 문제에서 비교해야 하는 두 양을 찾아보자. 소금과 소금물 중 어떤 것이 전체 양일까?"
          : "좋아, 중심 문장이 말하는 핵심을 먼저 보자. 바다가 우리에게 주는 필요한 것인지 하나씩 확인해볼까?",
      },
    ];
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

function getTextMessageContent(messages: ResponseMessage[]) {
  const textMessage = messages.find((message) => message.type === "text");

  return textMessage?.type === "text" ? textMessage.content : undefined;
}

function getBubbleActions(
  messages: ResponseMessage[],
  stepId: DemoStepId,
  caseId: DemoCaseId,
): PorongBubbleAction[] {
  const choicesMessage = messages.find((message) => message.type === "choices");

  if (choicesMessage?.type === "choices") {
    return choicesMessage.items.map((item) =>
      resolveBubbleAction(item, stepId, caseId),
    );
  }

  return getDefaultBubbleActions(stepId, caseId);
}

function resolveBubbleAction(
  item: ChoiceSelection,
  stepId: DemoStepId,
  caseId: DemoCaseId,
): PorongBubbleAction {
  const label = item.label;
  const isUpper = caseId === "upper-math";

  if (item.id === "start_learning" || label.includes("학습시작")) {
    return {
      ...item,
      action: "navigate",
      targetStep: "learning",
      targetTaskIndex: 0,
    };
  }

  if (item.id === "continue_next_task" || label.includes("다음")) {
    return {
      ...item,
      action: "navigate",
      targetStep: "learning",
      targetTaskIndex: 1,
    };
  }

  if (item.id === "continue_current_problem" || label.includes("한 문제")) {
    return {
      ...item,
      action: "navigate",
      targetStep: "learning",
      targetTaskIndex: 1,
    };
  }

  if (item.id === "ask_hint" || label.includes("힌트")) {
    return {
      ...item,
      action: "open_chat",
      targetStep: "help",
      targetTaskIndex: isUpper ? 1 : 0,
    };
  }

  if (
    item.id === "review_wrong_answers" ||
    label.includes("복습")
  ) {
    return {
      ...item,
      action: "navigate",
      targetStep: "wrapup",
    };
  }

  if (
    item.id === "finish_today" ||
    item.id === "end_today" ||
    label.includes("여기까지")
  ) {
    return {
      ...item,
      action: "navigate",
      targetStep: "home",
    };
  }

  if (item.id === "back_home" || label.includes("홈")) {
    return {
      ...item,
      action: "navigate",
      targetStep: "home",
    };
  }

  return {
    ...item,
    action: "navigate",
    targetStep: "learning",
  };
}

function getDefaultBubbleActions(
  stepId: DemoStepId,
  caseId: DemoCaseId,
): PorongBubbleAction[] {
  const isUpper = caseId === "upper-math";

  if (stepId === "home") {
    return [
      {
        id: "start_learning",
        label: isUpper ? "수학 풀러가기" : "국어 시작하기",
        action: "navigate",
        targetStep: "learning",
        targetTaskIndex: 0,
      },
    ];
  }

  if (stepId === "complete") {
    const continueAction: PorongBubbleAction = {
      id: "continue_next_task",
      label: isUpper ? "국어 하러가기" : "심화 국어 도전하기",
      action: "navigate",
      targetStep: "learning",
      targetTaskIndex: 1,
    };

    return isUpper
      ? [
          continueAction,
          {
            id: "end_today",
            label: "오늘은 여기까지",
            action: "navigate",
            targetStep: "home",
          },
        ]
      : [continueAction];
  }

  if (stepId === "exit") {
    return [
      {
        id: "continue_current_problem",
        label: "마저 하기",
        action: "navigate",
        targetStep: "learning",
        targetTaskIndex: 1,
      },
      {
        id: "ask_hint",
        label: "힌트 받고 풀기",
        action: "open_chat",
        targetStep: "help",
        targetTaskIndex: isUpper ? 1 : 0,
      },
    ];
  }

  if (stepId === "wrapup") {
    return [
      {
        id: isUpper ? "review_wrong_answers" : "finish_today",
        label: isUpper ? "복습하러 가기" : "완료하기",
        action: "navigate",
        targetStep: "home",
      },
    ];
  }

  return [];
}

function getPorongState({
  stepId,
  chatOpen,
  isStreaming,
}: {
  stepId: DemoStepId;
  chatOpen: boolean;
  isStreaming: boolean;
}): PorongOverlayState {
  if (isStreaming) {
    return "thinking";
  }

  if (chatOpen) {
    return stepId === "help" ? "hint" : "speaking";
  }

  if (stepId === "home") {
    return "welcome";
  }

  if (stepId === "complete") {
    return "cheer";
  }

  if (stepId === "wrapup") {
    return "comfort";
  }

  if (stepId === "exit") {
    return "comfort";
  }

  return "idle";
}

function isTextEntryTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  const tagName = target.tagName.toLowerCase();

  return (
    target.isContentEditable ||
    tagName === "input" ||
    tagName === "textarea" ||
    tagName === "select"
  );
}

function replaceDemoUrl({
  caseId,
  demoMode,
  showDemoControls,
}: {
  caseId: DemoCaseId;
  demoMode: DemoRunMode;
  showDemoControls: boolean;
}) {
  const url = new URL(window.location.href);

  url.searchParams.set("case", caseId);

  if (demoMode === "hybrid") {
    url.searchParams.set("mode", "hybrid");
  } else {
    url.searchParams.delete("mode");
  }

  if (showDemoControls) {
    url.searchParams.set("controls", "1");
  } else {
    url.searchParams.delete("controls");
  }

  const query = url.searchParams.toString();
  window.history.replaceState(
    null,
    "",
    `${url.pathname}${query ? `?${query}` : ""}${url.hash}`,
  );
}

export function SmartAllCoachApp({
  showDemoControls = false,
  initialCaseId = "lower-korean",
  demoMode = "script",
  chatAdapter,
}: SmartAllCoachAppProps) {
  const [caseId, setCaseId] = useState<DemoCaseId>(initialCaseId);
  const [stepId, setStepId] = useState<DemoStepId>("home");
  const [flowStageId, setFlowStageId] = useState<DemoFlowStageId>("home");
  const [activeTaskIndex, setActiveTaskIndex] = useState(0);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [bubbleResponseMessages, setBubbleResponseMessages] = useState<
    ResponseMessage[] | null
  >(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [chatError, setChatError] = useState("");
  const [demoRunSeq, setDemoRunSeq] = useState(0);
  const [lowerSecondSelectedChoiceId, setLowerSecondSelectedChoiceId] =
    useState<string | null>(null);
  const [lowerSecondCoachReady, setLowerSecondCoachReady] = useState(false);
  const reactRunId = useId();
  const demoRunId = `${reactRunId}-${demoRunSeq}`.replace(/[^a-zA-Z0-9_-]/g, "");
  const tabletRef = useRef<HTMLDivElement | null>(null);
  const turnIdRef = useRef(0);
  const streamRunRef = useRef(0);
  const lowerSecondResolutionTimerRef = useRef<ReturnType<
    typeof setTimeout
  > | null>(null);
  const resolvedChatAdapter =
    demoMode === "script" ? mockChatAdapter : chatAdapter ?? defaultChatAdapter;

  const demoCase = demoCases[caseId];
  const fallbackBubbleMessages = getFallbackBubbleMessages(
    caseId,
    stepId,
    flowStageId,
  );
  const shouldRequestBubble =
    !chatOpen &&
    bubbleResponseMessages === null &&
    ["home", "complete", "exit", "wrapup"].includes(stepId) &&
    flowStageId !== "upper_review";
  const bubbleMessages =
    bubbleResponseMessages ?? (isStreaming ? [] : fallbackBubbleMessages);
  const shouldShowLearningHintBubble =
    caseId === "lower-korean" &&
    stepId === "learning" &&
    activeTaskIndex === 0 &&
    !chatOpen;
  const bubbleText = getTextMessageContent(bubbleMessages);
  const visibleBubbleText =
    shouldShowLearningHintBubble
      ? "궁금한 게 있으면 언제든 나를 눌러서 물어봐줘"
      : bubbleText ?? (isStreaming && shouldRequestBubble ? THINKING_BUBBLE_TEXT : undefined);
  const bubbleActions = shouldShowLearningHintBubble
    ? []
    : getBubbleActions(bubbleMessages, stepId, caseId);
  const isUpper = caseId === "upper-math";
  const activeTask = demoCase.tasks[activeTaskIndex] ?? demoCase.tasks[0];
  const shouldShowBubble =
    !chatOpen &&
    ((["home", "complete", "exit", "wrapup"].includes(stepId) &&
      flowStageId !== "upper_review") ||
      shouldShowLearningHintBubble);
  const activeTouchpoint =
    flowStageId === "upper_review"
      ? undefined
      : demoCase.touchpointByStep[stepId];
  const porongState = getPorongState({
    stepId,
    chatOpen,
    isStreaming,
  });
  useEffect(() => {
    if (!shouldRequestBubble) {
      return;
    }

    const runId = streamRunRef.current + 1;
    const request = makeChatRequest(caseId, stepId, "", "init", {
      activeTaskIndex,
      threadIdSuffix: demoRunId,
      context: getFlowContext(caseId, flowStageId),
    });

    streamRunRef.current = runId;

    async function loadBubbleMessages() {
      const messages: ResponseMessage[] = [];

      try {
        await Promise.resolve();
        if (streamRunRef.current !== runId) {
          return;
        }

        setBubbleResponseMessages(null);
        setChatError("");
        setIsStreaming(true);

        for await (const message of resolvedChatAdapter(request, { caseId, stepId })) {
          if (streamRunRef.current !== runId) {
            return;
          }

          messages.push(message);
          setBubbleResponseMessages([...messages]);
        }
      } catch {
        if (streamRunRef.current === runId) {
          setBubbleResponseMessages(
            getFallbackBubbleMessages(caseId, stepId, flowStageId),
          );
          setChatError("");
        }
      } finally {
        if (streamRunRef.current === runId) {
          setIsStreaming(false);
        }
      }
    }

    void loadBubbleMessages();
  }, [activeTaskIndex, caseId, stepId, flowStageId, resolvedChatAdapter, shouldRequestBubble, demoRunId]);

  const makeTurnId = () => {
    turnIdRef.current += 1;
    return `turn-${streamRunRef.current}-${turnIdRef.current}`;
  };

  const makeStudentTurn = (content: string): ChatTurn => ({
    id: makeTurnId(),
    role: "student",
    content,
  });

  const makeCoachTurn = (message: ResponseMessage): ChatTurn => ({
    id: makeTurnId(),
    role: "coach",
    message,
  });

  const stopCurrentStream = useCallback(() => {
    streamRunRef.current += 1;
    setIsStreaming(false);
    setChatError("");
  }, []);

  const clearLowerSecondResolutionTimer = useCallback(() => {
    if (lowerSecondResolutionTimerRef.current) {
      clearTimeout(lowerSecondResolutionTimerRef.current);
      lowerSecondResolutionTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return clearLowerSecondResolutionTimer;
  }, [clearLowerSecondResolutionTimer]);

  const sendToAdapter = async ({
    targetStepId,
    content = "",
    messageType,
    reset,
    requestTaskIndex,
    requestContext,
  }: {
    targetStepId: DemoStepId;
    content?: string;
    messageType?: IncomingMessageType;
    reset: boolean;
    requestTaskIndex?: number;
    requestContext?: Partial<ChatRequestContext>;
  }) => {
    const runId = streamRunRef.current + 1;
    const request = makeChatRequest(caseId, targetStepId, content, messageType, {
      activeTaskIndex: requestTaskIndex ?? activeTaskIndex,
      threadIdSuffix: demoRunId,
      context: {
        ...getFlowContext(caseId, flowStageId),
        ...requestContext,
      },
    });

    streamRunRef.current = runId;
    setChatError("");

    if (reset) {
      setChatTurns(content ? [makeStudentTurn(content)] : []);
    } else if (content) {
      setChatTurns((current) => [...current, makeStudentTurn(content)]);
    }

    setIsStreaming(true);

    try {
      for await (const message of resolvedChatAdapter(request, {
        caseId,
        stepId: targetStepId,
      })) {
        if (streamRunRef.current !== runId) {
          return;
        }

        setChatTurns((current) => [...current, makeCoachTurn(message)]);
      }
    } catch (error) {
      if (streamRunRef.current === runId) {
        const fallbackMessages = getFallbackChatMessages(
          caseId,
          targetStepId,
          messageType,
          content,
          requestTaskIndex ?? activeTaskIndex,
        );
        if (fallbackMessages.length > 0) {
          setChatTurns((current) => [
            ...current,
            ...fallbackMessages.map((message) => makeCoachTurn(message)),
          ]);
          setChatError("");
        } else {
          setChatError(
            error instanceof Error
              ? error.message
              : "코치 응답을 불러오지 못했어요.",
          );
        }
      }
    } finally {
      if (streamRunRef.current === runId) {
        setIsStreaming(false);
      }
    }
  };

  const startChatPanel = (
    targetStepId: DemoStepId,
    content = "",
    messageType?: IncomingMessageType,
    requestTaskIndex?: number,
    requestContext?: Partial<ChatRequestContext>,
  ) => {
    setStepId(targetStepId);
    setChatOpen(true);

    void sendToAdapter({
      targetStepId,
      content,
      messageType: messageType ?? (content ? "choice" : "init"),
      reset: true,
      requestTaskIndex,
      requestContext,
    });
  };

  const setCase = useCallback((nextCaseId: DemoCaseId) => {
    clearLowerSecondResolutionTimer();
    stopCurrentStream();
    setDemoRunSeq((current) => current + 1);
    setCaseId(nextCaseId);
    setActiveTaskIndex(0);
    setStepId("home");
    setFlowStageId("home");
    setChatOpen(false);
    setChatTurns([]);
    setBubbleResponseMessages(null);
    setLowerSecondSelectedChoiceId(null);
    setLowerSecondCoachReady(false);
  }, [clearLowerSecondResolutionTimer, stopCurrentStream]);

  useEffect(() => {
    const handleDemoShortcut = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        isTextEntryTarget(event.target)
      ) {
        return;
      }

      if (event.code === "Digit1" || event.key === "1") {
        event.preventDefault();
        replaceDemoUrl({
          caseId: "lower-korean",
          demoMode,
          showDemoControls,
        });
        setCase("lower-korean");
        return;
      }

      if (event.code === "Digit2" || event.key === "2") {
        event.preventDefault();
        replaceDemoUrl({
          caseId: "upper-math",
          demoMode,
          showDemoControls,
        });
        setCase("upper-math");
        return;
      }

      if (event.code === "KeyR" || event.key.toLowerCase() === "r") {
        event.preventDefault();
        replaceDemoUrl({
          caseId,
          demoMode,
          showDemoControls,
        });
        setCase(caseId);
      }
    };

    window.addEventListener("keydown", handleDemoShortcut);

    return () => {
      window.removeEventListener("keydown", handleDemoShortcut);
    };
  }, [caseId, demoMode, setCase, showDemoControls]);

  const openTask = (taskIndex: number) => {
    clearLowerSecondResolutionTimer();
    stopCurrentStream();
    setActiveTaskIndex(taskIndex);
    setStepId("learning");
    setFlowStageId("learning");
    setChatOpen(false);
    setChatTurns([]);
    setBubbleResponseMessages(null);
    setLowerSecondSelectedChoiceId(null);
    setLowerSecondCoachReady(false);
  };

  const moveToStep = (nextStepId: DemoStepId) => {
    stopCurrentStream();

    if (nextStepId === "help") {
      startChatPanel("help", "", "init", activeTaskIndex, {
        ...getFlowContext(caseId, flowStageId),
        flow_event: "porong_help_opened",
      });
      return;
    }

    if (nextStepId === "learning") {
      openTask(activeTaskIndex);
      return;
    }

    if (nextStepId === "complete") {
      setFlowStageId(caseId === "upper-math" ? "upper_math_complete" : "lower_first_correct");
    } else if (nextStepId === "exit") {
      setFlowStageId(caseId === "upper-math" ? "learning" : "lower_second_exit");
    } else if (nextStepId === "wrapup") {
      setFlowStageId(caseId === "upper-math" ? "upper_today_done" : "lower_final");
    } else {
      setFlowStageId("home");
      setActiveTaskIndex(0);
    }

    setStepId(nextStepId);
    setChatOpen(false);
    setChatTurns([]);
    setBubbleResponseMessages(null);
  };

  const openLearning = () => {
    openTask(0);
  };

  const openHelpPanel = () => {
    startChatPanel("help", "", "init", activeTaskIndex, {
      ...getFlowContext(caseId, flowStageId),
      flow_event: "porong_help_opened",
    });
  };

  const openCoachForCurrentStep = () => {
    if (stepId === "learning") {
      openHelpPanel();
      return;
    }

    startChatPanel(stepId, "", "init", activeTaskIndex, getFlowContext(caseId, flowStageId));
  };

  const showCompletionExitRewardPrompt = () => {
    stopCurrentStream();
    setChatOpen(false);
    setChatTurns([]);
    setBubbleResponseMessages([
      {
        type: "text",
        content:
          "오늘의 학습을 완료하면 보상으로 별 10개를 받을 수 있어! 나와 함께 끝까지 해보자",
      },
    ]);
  };

  const applyTargetTask = (action: PorongBubbleAction) => {
    if (typeof action.targetTaskIndex === "number") {
      setActiveTaskIndex(action.targetTaskIndex);
    }
  };

  const navigateFromBubble = (action: PorongBubbleAction) => {
    applyTargetTask(action);

    if (action.id === "review_wrong_answers") {
      setFlowStageId("upper_review");
      setStepId("wrapup");
      setChatOpen(false);
      setBubbleResponseMessages(null);
      return;
    }

    if (action.id === "finish_today") {
      setFlowStageId("lower_final");
      setStepId("home");
      setActiveTaskIndex(0);
      setChatOpen(false);
      setBubbleResponseMessages([
        {
          type: "text",
          content: "모든 학습을 끝냈구나 멋지다. 내일 또 봐~",
        },
        {
          type: "choices",
          items: [],
        },
      ]);
      return;
    }

    if (typeof action.targetTaskIndex === "number") {
      openTask(action.targetTaskIndex);
      return;
    }

    moveToStep(action.targetStep ?? "learning");
  };

  const handleBubbleChoice = (action: PorongBubbleAction) => {
    applyTargetTask(action);

    if (action.action === "open_chat") {
      startChatPanel(
        action.targetStep ?? stepId,
        action.label,
        "choice",
        action.targetTaskIndex,
        getFlowContext(caseId, flowStageId),
      );
      return;
    }

    navigateFromBubble(action);
  };

  const handleChatChoice = (choice: ChoiceSelection) => {
    if (isStreaming) {
      return;
    }

    if (
      caseId === "lower-korean" &&
      activeTaskIndex === 1 &&
      choice.id === "sea_good_points"
    ) {
      setLowerSecondCoachReady(true);
    }

    void sendToAdapter({
      targetStepId: stepId,
      content: choice.label,
      messageType: "choice",
      reset: false,
    });
  };

  const handleChatTextSubmit = (content: string) => {
    if (isStreaming || content.trim() === "") {
      return;
    }

    void sendToAdapter({
      targetStepId: stepId,
      content: content.trim(),
      messageType: "text",
      reset: false,
    });
  };

  const completeCurrentLearning = () => {
    stopCurrentStream();
    setChatOpen(false);
    setChatTurns([]);
    setBubbleResponseMessages(null);

    if (caseId === "lower-korean") {
      if (activeTaskIndex === 0) {
        setFlowStageId("lower_first_correct");
        setStepId("complete");
        return;
      }

      if (flowStageId === "lower_second_corrected") {
        return;
      }

      if (flowStageId === "lower_second_wrong") {
        if (
          lowerSecondCoachReady &&
          lowerSecondSelectedChoiceId === "4"
        ) {
          clearLowerSecondResolutionTimer();
          setChatOpen(false);
          setChatTurns([]);
          setFlowStageId("lower_second_corrected");
          setStepId("learning");
          lowerSecondResolutionTimerRef.current = setTimeout(() => {
            lowerSecondResolutionTimerRef.current = null;
            setFlowStageId("lower_final");
            setStepId("wrapup");
          }, 3000);
          return;
        }

        setFlowStageId("lower_final");
        setStepId("wrapup");
        return;
      }

      setFlowStageId("lower_second_wrong");
      setStepId("learning");
      return;
    }

    if (activeTaskIndex === 0) {
      setFlowStageId("upper_math_complete");
      setStepId("complete");
      return;
    }

    setFlowStageId("upper_today_done");
    setStepId("wrapup");
  };

  const handleAnswerSubmit = (
    result: Exclude<AnswerResult, null>,
    choiceId?: string,
  ) => {
    if (caseId === "lower-korean") {
      if (activeTaskIndex === 0) {
        stopCurrentStream();
        setFlowStageId("lower_first_correct");
        setStepId("learning");
        setChatOpen(false);
        setChatTurns([]);
        setBubbleResponseMessages(null);
        return;
      }

      if (flowStageId === "lower_second_corrected") {
        return;
      }

      if (choiceId) {
        setLowerSecondSelectedChoiceId(choiceId);
      }

      if (result === "correct") {
        completeCurrentLearning();
      } else {
        setFlowStageId("lower_second_wrong");
        setStepId("learning");
      }

      return;
    }

    completeCurrentLearning();
  };

  return (
    <InteractionZoneProvider>
      <main className="demo-page">
      <section
        ref={tabletRef}
        className={`smartall-tablet ${isUpper ? "theme-upper" : "theme-lower"}`}
        aria-label="스마트올 AI 학습코치 목업"
      >
        <SmartAllTopNav />

        {stepId === "home" && (
          <HomeScreen
            caseId={caseId}
            activeTaskIndex={activeTaskIndex}
            flowStageId={flowStageId}
            onStartLearning={openLearning}
          />
        )}

        {(stepId === "learning" || stepId === "help" || stepId === "exit") && (
          <LearningScreen
            caseId={caseId}
            activeTask={activeTask}
            activeTaskIndex={activeTaskIndex}
            flowStageId={flowStageId}
            isHelpOpen={chatOpen}
            isExitMoment={stepId === "exit"}
            onComplete={completeCurrentLearning}
            onExit={() => moveToStep("exit")}
            onAnswerSubmit={handleAnswerSubmit}
          />
        )}

        {(stepId === "complete" || stepId === "wrapup") && (
          <CompletionScreen
            caseId={caseId}
            activeTaskIndex={activeTaskIndex}
            flowStageId={flowStageId}
            onExit={showCompletionExitRewardPrompt}
          />
        )}

        <PorongOverlay
          stageRef={tabletRef}
          touchpoint={activeTouchpoint}
          state={porongState}
          chatOpen={chatOpen}
          snapBackToDefault
          showBubble={shouldShowBubble}
          bubbleText={visibleBubbleText}
          bubbleActions={bubbleActions}
          onTap={openCoachForCurrentStep}
          onBubbleAction={handleBubbleChoice}
        />

        <PorongCoachPanel
          isOpen={chatOpen}
          turns={chatTurns}
          isBusy={isStreaming}
          errorMessage={chatError}
          onClose={() => setChatOpen(false)}
          onChoice={handleChatChoice}
          onTextSubmit={handleChatTextSubmit}
        />
      </section>

      {showDemoControls && (
        <DemoControls
          caseId={caseId}
          stepId={stepId}
          onCaseChange={setCase}
          onStepChange={moveToStep}
        />
      )}
      </main>
    </InteractionZoneProvider>
  );
}

function SmartAllTopNav() {
  return (
    <header className="smartall-top-nav">
      <div className="brand-area" aria-label="웅진 스마트올">
        <span className="brand-chevron">⌄</span>
        <span className="brand-logo">
          <span className="brand-small">웅진씽크빅</span>
          <span className="brand-main">
            smart<span>All</span>
          </span>
        </span>
      </div>

      <nav className="smartall-tabs" aria-label="스마트올 상단 메뉴">
        <span className="active">오늘의 학습</span>
        <span>AI맞춤</span>
        <span>단원평가센터</span>
        <span>쉬는시간</span>
      </nav>

      <div className="top-tools" aria-label="상단 도구">
        <button type="button">전체</button>
        <span aria-hidden="true">⌕</span>
        <span aria-hidden="true">☆</span>
        <span aria-hidden="true">▱</span>
        <span aria-hidden="true">☰</span>
      </div>
    </header>
  );
}

function HomeScreen({
  caseId,
  activeTaskIndex,
  flowStageId,
  onStartLearning,
}: {
  caseId: DemoCaseId;
  activeTaskIndex: number;
  flowStageId: DemoFlowStageId;
  onStartLearning: () => void;
}) {
  const isUpper = caseId === "upper-math";
  const demoCase = demoCases[caseId];
  const primaryTask = demoCase.tasks[0];
  const activeSubject = primaryTask?.subject ?? "국어";

  return (
    <div className="home-screen">
      <div className={`home-grid today-home-grid ${isUpper ? "upper-home-grid" : ""}`}>
        {!isUpper && (
          <SubjectRail
            subjects={subjectsByCase[caseId]}
            activeSubject={activeSubject}
          />
        )}

        <InteractionZone
          id="learning-card"
          label="오늘의 학습 카드"
          type="content"
          className="study-zone"
          role="region"
          ariaLabel="오늘의 학습 카드"
        >
          {isUpper ? (
            <UpperSubjectCards onStartLearning={onStartLearning} />
          ) : (
            <TodayHeroCard
              caseId={caseId}
              flowStageId={flowStageId}
              onStartLearning={onStartLearning}
            />
          )}
        </InteractionZone>

        <SmartAllRightRail
          caseId={caseId}
          activeTaskIndex={activeTaskIndex}
          flowStageId={flowStageId}
        />
      </div>
    </div>
  );
}

function UpperSubjectCards({
  onStartLearning,
}: {
  onStartLearning: () => void;
}) {
  const cards = [
    {
      title: "수학",
      subtitle: "비와 비율",
      tone: "blue",
      zoneId: "subject-math" as const,
    },
    {
      title: "국어",
      subtitle: "정보와 표현 판단하기",
      tone: "green",
      zoneId: "subject-korean" as const,
    },
    {
      title: "과학",
      subtitle: "생태계와 환경",
      tone: "mint",
      zoneId: "subject-science" as const,
    },
    {
      title: "사회",
      subtitle: "세계 여러 나라",
      tone: "white",
      zoneId: "subject-social" as const,
    },
  ];

  return (
    <div className="upper-card-grid">
      {cards.map((card) => (
        <InteractionZone
          key={card.title}
          id={card.zoneId}
          label={card.title}
          type="subject"
          className="upper-card-zone"
        >
          <button
            type="button"
            className={`upper-card ${card.tone}`}
            onClick={onStartLearning}
          >
            <span className="card-title">{card.title}</span>
            <span className="card-star">★</span>
            <strong>{card.subtitle}</strong>
            <span className="upper-card-art" aria-hidden="true" />
          </button>
        </InteractionZone>
      ))}
    </div>
  );
}

function SubjectRail({
  subjects,
  activeSubject,
}: {
  subjects: string[];
  activeSubject: string;
}) {
  return (
    <aside className="subject-rail" aria-label="과목 순서">
      {subjects.map((subject, index) => (
        <InteractionZone
          key={subject}
          id={getSubjectZoneId(subject)}
          label={subject}
          type="subject"
        >
          <button
            type="button"
            className={subject === activeSubject ? "active" : ""}
          >
            <span>{index + 1}</span>
            {subject}
          </button>
        </InteractionZone>
      ))}
    </aside>
  );
}

function getSubjectZoneId(subject: string): InteractionZoneId {
  if (subject.startsWith("국어")) {
    return "subject-korean";
  }

  if (subject === "문해력") {
    return "subject-literacy";
  }

  if (subject === "한자") {
    return "subject-hanja";
  }

  if (subject === "과학") {
    return "subject-science";
  }

  if (subject === "사회") {
    return "subject-social";
  }

  return "subject-math";
}

function TodayHeroCard({
  caseId,
  flowStageId,
  onStartLearning,
}: {
  caseId: DemoCaseId;
  flowStageId: DemoFlowStageId;
  onStartLearning: () => void;
}) {
  const isUpper = caseId === "upper-math";
  const isLowerAllDone = caseId === "lower-korean" && flowStageId === "lower_final";
  const hero = isUpper
    ? {
        subject: "수학",
        title: "비와 비율",
        description: "소금물의 비율을 차근차근 알아볼까요",
        unit: "6학년 수학 · 비율과 비례식",
      }
    : {
        subject: "국어",
        title: "문단의 짜임",
        description: "긴글에서 필요한 정보를 빠르게 찾아볼까요",
        unit: "2학년 국어 · 긴글 이해하기",
      };

  return (
    <article className="lower-hero-card">
      <div className="hero-copy">
        <span className="subject-name">{hero.subject}</span>
        <h1>{hero.title}</h1>
        <p>{hero.description}</p>
        <small>{hero.unit}</small>
      </div>

      <div className="story-illustration" aria-hidden="true">
        <div className="story-sky" />
      </div>

      <button
        type="button"
        className={`primary-study-button ${isLowerAllDone ? "is-complete" : ""}`}
        aria-disabled={isLowerAllDone}
        onClick={isLowerAllDone ? undefined : onStartLearning}
      >
        <span aria-hidden="true">{isLowerAllDone ? "✓" : "▶"}</span>
        {isLowerAllDone ? "학습 성공!" : "학습시작"}
      </button>
    </article>
  );
}

function SmartAllRightRail({
  caseId,
  activeTaskIndex,
  flowStageId,
}: {
  caseId: DemoCaseId;
  activeTaskIndex: number;
  flowStageId: DemoFlowStageId;
}) {
  return (
    <aside className="right-rail today-right-rail" aria-label="AI 학습코치 영역">
      <TodayTaskStatusCard
        caseId={caseId}
        activeTaskIndex={activeTaskIndex}
        flowStageId={flowStageId}
      />
    </aside>
  );
}

function TodayTaskStatusCard({
  caseId,
  activeTaskIndex,
  flowStageId,
}: {
  caseId: DemoCaseId;
  activeTaskIndex: number;
  flowStageId: DemoFlowStageId;
}) {
  const isUpper = caseId === "upper-math";
  const accentClass = isUpper ? "accent-blue" : "accent-orange";
  const subjects = subjectsByCase[caseId];
  const completedAll =
    flowStageId === "lower_final" ||
    flowStageId === "upper_today_done" ||
    flowStageId === "upper_review";
  const highlightedIndex = completedAll
    ? subjects.length - 1
    : Math.min(activeTaskIndex, subjects.length - 1);

  return (
    <section className={`today-task-card ${accentClass}`} aria-label="오늘의 학습">
      <header>
        <strong>오늘의 학습</strong>
        <span aria-hidden="true">✎</span>
      </header>
      <div className="today-task-list">
        {subjects.map((subject, index) => (
          <span
            key={subject}
            className={index <= highlightedIndex ? "active" : ""}
          >
            {subject}
          </span>
        ))}
      </div>
    </section>
  );
}

function LearningScreen({
  caseId,
  activeTask,
  activeTaskIndex,
  flowStageId,
  isHelpOpen,
  isExitMoment,
  onComplete,
  onExit,
  onAnswerSubmit,
}: {
  caseId: DemoCaseId;
  activeTask?: TaskRef;
  activeTaskIndex: number;
  flowStageId: DemoFlowStageId;
  isHelpOpen: boolean;
  isExitMoment: boolean;
  onComplete: () => void;
  onExit: () => void;
  onAnswerSubmit: (
    result: Exclude<AnswerResult, null>,
    choiceId?: string,
  ) => void;
}) {
  const isUpper = caseId === "upper-math";
  const subject = activeTask?.subject ?? (isUpper ? "수학" : "국어");
  const unit = activeTask?.unit ?? (isUpper ? "비와 비율" : "긴글 이해하기");
  const isUpperMathProblem = isUpper && subject === "수학";
  const answerResult: AnswerResult =
    flowStageId === "lower_first_correct"
      ? "correct"
      : flowStageId === "lower_second_wrong"
        ? "incorrect"
        : flowStageId === "lower_second_corrected"
          ? "corrected"
          : null;
  const primaryActionLabel = "완료";

  return (
    <div
      className={[
        "learning-screen",
        isHelpOpen ? "with-panel" : "",
        isUpperMathProblem ? "upper-math-problem-layout" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="learning-layout">
        <section className="learning-board" aria-label="학습 문제 화면">
          <div className="lesson-header">
            <InteractionZone
              id="exit-button"
              label="나가기"
              type="primary-action"
            >
              <button type="button" onClick={onExit}>
                나가기
              </button>
            </InteractionZone>
            <div className="lesson-title">
              <span>{subject} · {unit}</span>
            </div>
            <span className="lesson-header-spacer" aria-hidden="true" />
          </div>

          {isUpper && subject === "국어" ? (
            <UpperKoreanProblem onAnswerSubmit={() => onAnswerSubmit("correct")} />
          ) : isUpper ? (
            <UpperMathProblem />
          ) : (
            <LowerKoreanProblem
              taskIndex={activeTaskIndex}
              answerResult={answerResult}
              onAnswerSubmit={onAnswerSubmit}
            />
          )}

          {isExitMoment && (
            <div className="exit-toast">
              나가기 전, 지금 문제를 조금만 더 이어볼 수 있어요.
            </div>
          )}

          <div className="lesson-actions">
            <InteractionZone
              id="complete-button"
              label="완료"
              type="primary-action"
            >
              <button type="button" className="primary-action" onClick={onComplete}>
                {primaryActionLabel}
              </button>
            </InteractionZone>
          </div>
        </section>
        <SmartAllRightRail
          caseId={caseId}
          activeTaskIndex={activeTaskIndex}
          flowStageId={flowStageId}
        />
      </div>
    </div>
  );
}

function LowerKoreanProblem({
  taskIndex,
  answerResult,
  onAnswerSubmit,
}: {
  taskIndex: number;
  answerResult: AnswerResult;
  onAnswerSubmit: (
    result: Exclude<AnswerResult, null>,
    choiceId?: string,
  ) => void;
}) {
  const isFirstTask = taskIndex === 0;
  const [selectedChoice, setSelectedChoice] = useState<{
    id: string;
    taskIndex: number;
  } | null>(null);
  const choices = isFirstTask
    ? [
        { id: "1", label: "물과 우유", result: "incorrect" as const },
        { id: "2", label: "나무와 물", result: "correct" as const },
        { id: "3", label: "종이와 우유", result: "incorrect" as const },
        { id: "4", label: "학교와 우유", result: "incorrect" as const },
      ]
    : [
        { id: "1", label: "바닷물로 소금을 만들 수 있습니다.", result: "incorrect" as const },
        { id: "2", label: "바닷속에는 많은 자원이 있습니다.", result: "incorrect" as const },
        { id: "3", label: "바다에서 물고기를 잡을 수 있습니다.", result: "incorrect" as const },
        { id: "4", label: "바다는 태풍 때 해일을 일으킬 수 있습니다.", result: "incorrect" as const },
      ];
  const answerMarkVariant =
    isFirstTask && answerResult === "correct"
      ? "circle"
      : !isFirstTask && answerResult === "incorrect"
        ? "slash"
        : !isFirstTask && answerResult === "corrected"
          ? "circle"
          : null;
  const feedbackClassName =
    answerResult === "incorrect" ? "incorrect" : "correct";
  const selectedChoiceId =
    selectedChoice?.taskIndex === taskIndex ? selectedChoice.id : null;

  const handleChoiceClick = (choice: (typeof choices)[number]) => {
    setSelectedChoice({ id: choice.id, taskIndex });
    onAnswerSubmit(isFirstTask ? "correct" : choice.result, choice.id);
  };

  return (
    <InteractionZone
      id="problem-board"
      label="현재 문제"
      type="content"
      className="problem-zone"
    >
      <article className={`problem-card korean-problem ${isFirstTask ? "basic-korean-problem" : "advanced-korean-problem"}`}>
        {answerMarkVariant && (
          <span
            className={`answer-result-mark ${answerMarkVariant}`}
            aria-hidden="true"
          />
        )}
        <span className="problem-count">{isFirstTask ? "국어 1" : "국어 2"}</span>
        <h1>
          {isFirstTask
            ? "글을 읽고 종이컵을 만들 때 필요한 것을 고르세요."
            : "중심 문장을 뒷받침하기에 알맞지 않은 문장을 고르세요."}
        </h1>
        <p>
          {isFirstTask
            ? "종이컵을 만들기 위해서는 종이의 원료가 되는 나무가 필요합니다. 또 물이 필요합니다."
            : "중심 문장: 바다에는 우리에게 필요한 여러 가지가 있습니다."}
        </p>
        {!isFirstTask && (
          <p>
            바다가 주는 필요한 것을 설명하는 문장인지 하나씩 살펴보세요.
          </p>
        )}
        <div className="answer-grid">
          {choices.map((choice) => (
            <button
              key={choice.id}
              type="button"
              className={selectedChoiceId === choice.id ? "is-selected" : ""}
              aria-pressed={selectedChoiceId === choice.id}
              onClick={() => handleChoiceClick(choice)}
            >
              {choice.label}
            </button>
          ))}
        </div>
        {answerResult && !isFirstTask && (
          <div className={`answer-feedback ${feedbackClassName}`}>
            {answerResult === "incorrect"
              ? "아쉽게 틀렸네요. 코치쌤을 눌러 물어볼까요?"
              : "정답이에요!"}
          </div>
        )}
      </article>
    </InteractionZone>
  );
}

function UpperMathProblem() {
  return (
    <InteractionZone
      id="problem-board"
      label="현재 문제"
      type="content"
      className="problem-zone"
    >
      <article className="problem-card math-problem">
        <span className="problem-count">문제 3</span>
        <h1>소금물의 양에 대한 소금의 양의 비율을 소수로 쓰세요.</h1>
        <p>
          (가) 비커에는 소금 37g을 녹여 소금물 148g을 만들었고, (나) 비커에는
          소금 76g을 녹여 소금물 380g을 만들었습니다.
        </p>
        <div className="ratio-board" aria-label="비율 문제 풀이 영역">
          <div>
            <span>소금</span>
            <strong>37g</strong>
            <strong>76g</strong>
          </div>
          <div>
            <span>소금물</span>
            <strong>148g</strong>
            <strong>380g</strong>
          </div>
        </div>
        <div className="equation-line">
          (가) <input aria-label="가 비커 정답 입력" placeholder="?" />
          <span> </span>
          (나) <input aria-label="나 비커 정답 입력" placeholder="?" />
        </div>
      </article>
    </InteractionZone>
  );
}

function UpperKoreanProblem({
  onAnswerSubmit,
}: {
  onAnswerSubmit: () => void;
}) {
  return (
    <InteractionZone
      id="problem-board"
      label="현재 문제"
      type="content"
      className="problem-zone"
    >
      <article className="problem-card korean-problem">
        <span className="problem-count">문제 1</span>
        <h1>정보와 표현이 알맞은지 판단해 보세요.</h1>
        <p>
          글에 나온 정보가 사실인지, 글쓴이의 생각인지 나누어 봅시다.
          다음 문장은 글쓴이의 생각에 가까운 표현입니다.
        </p>
        <div className="answer-grid">
          {[
            "사실 정보",
            "글쓴이의 생각",
            "문제와 상관없는 표현",
          ].map((answer) => (
            <button key={answer} type="button" onClick={onAnswerSubmit}>
              {answer}
            </button>
          ))}
        </div>
      </article>
    </InteractionZone>
  );
}

function CompletionScreen({
  caseId,
  activeTaskIndex,
  flowStageId,
  onExit,
}: {
  caseId: DemoCaseId;
  activeTaskIndex: number;
  flowStageId: DemoFlowStageId;
  onExit: () => void;
}) {
  const isUpper = caseId === "upper-math";
  const isReview = flowStageId === "upper_review";
  const isTodayDone = flowStageId === "upper_today_done";
  const isLowerAllDone = flowStageId === "lower_final";
  const description = isReview
    ? "오늘 틀렸던 문제만 가볍게 다시 볼 수 있어요."
    : isTodayDone
      ? "수학과 국어를 끝까지 해낸 뒤, 짧은 복습으로 마무리할 수 있어요."
      : isLowerAllDone
        ? "오늘의 학습 4개를 전부 완료했어요~"
      : isUpper
        ? "AI 코치가 다음 학습을 짧게 이어갈 수 있게 추천해 줄 거예요."
        : "오늘의 학습 4개 중 1개를 완료했어요~";

  return (
    <div className="completion-screen">
      <div className="completion-layout">
        <InteractionZone
          id="completion-card"
          label="학습 완료"
          type="content"
          className="completion-card"
          role="region"
          ariaLabel="학습 완료 화면"
        >
          <button type="button" className="completion-exit-button" onClick={onExit}>
            나가기
          </button>
          <div className="complete-medal" aria-hidden="true">
            ✓
          </div>
          <h1>
            {isReview
              ? "오답 복습으로 이동했어요"
              : isTodayDone
                ? "오늘의 학습을 모두 마쳤어요"
                : isLowerAllDone
                  ? "모든 학습을 완료했어요!"
                : isUpper
                ? "비와 비율을 끝냈어요"
                : "국어를 완료했어요"}
          </h1>
          {description && <p>{description}</p>}

          <div className="completion-stats">
            <div>
              <strong>{isUpper ? "86" : "100"}</strong>
              <span>점수</span>
            </div>
            <div>
              <strong>{isUpper ? "1" : "0"}</strong>
              <span>남은 오답</span>
            </div>
            <div>
              <strong>{isUpper ? "7분" : "3분"}</strong>
              <span>학습 시간</span>
            </div>
          </div>

        </InteractionZone>
        <SmartAllRightRail
          caseId={caseId}
          activeTaskIndex={activeTaskIndex}
          flowStageId={flowStageId}
        />
      </div>
    </div>
  );
}

function DemoControls({
  caseId,
  stepId,
  onCaseChange,
  onStepChange,
}: {
  caseId: DemoCaseId;
  stepId: DemoStepId;
  onCaseChange: (caseId: DemoCaseId) => void;
  onStepChange: (stepId: DemoStepId) => void;
}) {
  return (
    <section className="demo-controls" aria-label="시연 화면 전환">
      <label className="student-select-label">
        <span>mock 학생</span>
        <select
          value={caseId}
          onChange={(event) => onCaseChange(event.target.value as DemoCaseId)}
        >
          {demoStudentOptions.map((student) => (
            <option key={student.studentId} value={student.caseId}>
              {student.label}
            </option>
          ))}
        </select>
      </label>

      <div className="control-group">
        {orderedSteps.map((nextStepId) => (
          <button
            key={nextStepId}
            type="button"
            className={stepId === nextStepId ? "active" : ""}
            onClick={() => onStepChange(nextStepId)}
          >
            {demoStepLabels[nextStepId]}
          </button>
        ))}
      </div>
    </section>
  );
}
