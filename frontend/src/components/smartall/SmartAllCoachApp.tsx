"use client";

import { useEffect, useRef, useState } from "react";
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
  makeChatRequest,
  mockChatAdapter,
} from "@/lib/mock-chat";
import type {
  ChatAdapter,
  ChoiceSelection,
  ChatTurn,
  DemoCaseId,
  DemoStepId,
  IncomingMessageType,
  ResponseMessage,
} from "@/types/chat";

type SmartAllCoachAppProps = {
  showDemoControls?: boolean;
  initialCaseId?: DemoCaseId;
  chatAdapter?: ChatAdapter;
};

const orderedSteps: DemoStepId[] = [
  "home",
  "learning",
  "help",
  "complete",
  "exit",
  "finish",
];

const subjectsByCase: Record<DemoCaseId, string[]> = {
  "lower-korean": ["국어", "수학", "문해력", "한자"],
  "upper-math": ["개념별따기", "수학", "과학", "사회"],
};

const THINKING_BUBBLE_TEXT = "뽀롱~ 생각 중이야...";

const defaultChatAdapter =
  process.env.NEXT_PUBLIC_UNGJI_CHAT_MODE === "live"
    ? liveChatAdapter
    : mockChatAdapter;

function getTextMessageContent(messages: ResponseMessage[]) {
  const textMessage = messages.find((message) => message.type === "text");

  return textMessage?.type === "text" ? textMessage.content : undefined;
}

function getBubbleActions(messages: ResponseMessage[]): PorongBubbleAction[] {
  const choicesMessage = messages.find((message) => message.type === "choices");

  if (choicesMessage?.type !== "choices") {
    return [];
  }

  return choicesMessage.items.map((item) => ({
    id: item.id,
    label: item.label,
  }));
}

function getPorongState({
  stepId,
  chatOpen,
  isStreaming,
  isUpper,
}: {
  stepId: DemoStepId;
  chatOpen: boolean;
  isStreaming: boolean;
  isUpper: boolean;
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

  if (stepId === "exit") {
    return "comfort";
  }

  if (stepId === "finish") {
    return isUpper ? "comfort" : "cheer";
  }

  return "idle";
}

export function SmartAllCoachApp({
  showDemoControls = false,
  initialCaseId = "lower-korean",
  chatAdapter = defaultChatAdapter,
}: SmartAllCoachAppProps) {
  const [caseId, setCaseId] = useState<DemoCaseId>(initialCaseId);
  const [stepId, setStepId] = useState<DemoStepId>("home");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [bubbleResponseMessages, setBubbleResponseMessages] = useState<
    ResponseMessage[] | null
  >(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [chatError, setChatError] = useState("");
  const tabletRef = useRef<HTMLDivElement | null>(null);
  const turnIdRef = useRef(0);
  const streamRunRef = useRef(0);

  const demoCase = demoCases[caseId];
  const shouldRequestBubble =
    !chatOpen && ["home", "complete", "exit", "finish"].includes(stepId);
  const bubbleMessages = bubbleResponseMessages ?? [];
  const bubbleText = getTextMessageContent(bubbleMessages);
  const visibleBubbleText =
    bubbleText ?? (isStreaming && shouldRequestBubble ? THINKING_BUBBLE_TEXT : undefined);
  const bubbleActions = getBubbleActions(bubbleMessages);
  const isUpper = caseId === "upper-math";
  const shouldShowBubble =
    !chatOpen && ["home", "complete", "exit", "finish"].includes(stepId);
  const activeTouchpoint = demoCase.touchpointByStep[stepId];
  const porongState = getPorongState({
    stepId,
    chatOpen,
    isStreaming,
    isUpper,
  });
  useEffect(() => {
    if (!shouldRequestBubble) {
      return;
    }

    const runId = streamRunRef.current + 1;
    const request = makeChatRequest(caseId, stepId, "", "init");

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

        for await (const message of chatAdapter(request, { caseId, stepId })) {
          if (streamRunRef.current !== runId) {
            return;
          }

          messages.push(message);
          setBubbleResponseMessages([...messages]);
        }
      } catch (error) {
        if (streamRunRef.current === runId) {
          setChatError(
            error instanceof Error
              ? error.message
              : "코치 응답을 불러오지 못했어요.",
          );
        }
      } finally {
        if (streamRunRef.current === runId) {
          setIsStreaming(false);
        }
      }
    }

    void loadBubbleMessages();
  }, [caseId, stepId, chatAdapter, shouldRequestBubble]);

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

  const stopCurrentStream = () => {
    streamRunRef.current += 1;
    setIsStreaming(false);
    setChatError("");
  };

  const sendToAdapter = async ({
    targetStepId,
    content = "",
    messageType,
    reset,
  }: {
    targetStepId: DemoStepId;
    content?: string;
    messageType?: IncomingMessageType;
    reset: boolean;
  }) => {
    const runId = streamRunRef.current + 1;
    const request = makeChatRequest(caseId, targetStepId, content, messageType);

    streamRunRef.current = runId;
    setChatError("");

    if (reset) {
      setChatTurns(content ? [makeStudentTurn(content)] : []);
    } else if (content) {
      setChatTurns((current) => [...current, makeStudentTurn(content)]);
    }

    setIsStreaming(true);

    try {
      for await (const message of chatAdapter(request, {
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
        setChatError(
          error instanceof Error
            ? error.message
            : "코치 응답을 불러오지 못했어요.",
        );
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
  ) => {
    setStepId(targetStepId);
    setChatOpen(true);

    void sendToAdapter({
      targetStepId,
      content,
      messageType: messageType ?? (content ? "choice" : "init"),
      reset: true,
    });
  };

  const setCase = (nextCaseId: DemoCaseId) => {
    stopCurrentStream();
    setCaseId(nextCaseId);
    setStepId("home");
    setChatOpen(false);
    setChatTurns([]);
    setBubbleResponseMessages(null);
  };

  const moveToStep = (nextStepId: DemoStepId) => {
    stopCurrentStream();

    if (nextStepId === "help") {
      startChatPanel("help");
      return;
    }

    setStepId(nextStepId);
    setChatOpen(false);
    setChatTurns([]);
    setBubbleResponseMessages(null);
  };

  const openLearning = () => {
    stopCurrentStream();
    setStepId("learning");
    setChatOpen(false);
    setChatTurns([]);
    setBubbleResponseMessages(null);
  };

  const openHelpPanel = () => {
    startChatPanel("help");
  };

  const openCoachForCurrentStep = () => {
    startChatPanel(stepId === "learning" ? "help" : stepId);
  };

  const handleBubbleChoice = (choice: ChoiceSelection) => {
    startChatPanel(stepId, choice.label, "choice");
  };

  const handleChatChoice = (choice: ChoiceSelection) => {
    if (isStreaming) {
      return;
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
            onStartLearning={openLearning}
          />
        )}

        {(stepId === "learning" || stepId === "help" || stepId === "exit") && (
          <LearningScreen
            caseId={caseId}
            isHelpOpen={chatOpen}
            isExitMoment={stepId === "exit"}
            onOpenHelp={openHelpPanel}
            onComplete={() => moveToStep("complete")}
            onExit={() => moveToStep("exit")}
          />
        )}

        {(stepId === "complete" || stepId === "finish") && (
          <CompletionScreen
            caseId={caseId}
            isFinal={stepId === "finish"}
            onFinish={() => moveToStep("finish")}
            onRestart={() => moveToStep("home")}
          />
        )}

        <PorongOverlay
          stageRef={tabletRef}
          touchpoint={activeTouchpoint}
          state={porongState}
          chatOpen={chatOpen}
          showBubble={shouldShowBubble}
          bubbleText={visibleBubbleText}
          bubbleActions={bubbleActions}
          onTap={openCoachForCurrentStep}
          onBubbleAction={handleBubbleChoice}
        />

        <PorongCoachPanel
          isOpen={chatOpen}
          title={`${demoCase.studentName} · ${demoCase.label}`}
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
  onStartLearning,
}: {
  caseId: DemoCaseId;
  onStartLearning: () => void;
}) {
  const isUpper = caseId === "upper-math";
  const demoCase = demoCases[caseId];

  return (
    <div className="home-screen">
      <WeekStrip isUpper={isUpper} />

      <div className={`home-grid ${isUpper ? "upper-grid" : "lower-grid"}`}>
        {!isUpper && (
          <SubjectRail
            subjects={subjectsByCase[caseId]}
            activeSubject="국어"
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
            <LowerHeroCard onStartLearning={onStartLearning} />
          )}
        </InteractionZone>

        <SmartAllRightRail
          caseId={caseId}
          studentName={demoCase.studentName}
        />
      </div>
    </div>
  );
}

function WeekStrip({ isUpper }: { isUpper: boolean }) {
  const days = ["월", "화", "수", "목", "금", "토", "일"];

  return (
    <div className="week-strip">
      <div className="date-pill">
        <span className="calendar-mark" aria-hidden="true" />
        <strong>{isUpper ? "10월 1일" : "7월 12일"}</strong>
        <span>수요일</span>
      </div>

      <div className="day-row" aria-label="이번 주 학습 현황">
        {days.map((day) => (
          <span
            key={day}
            className={day === "수" ? "today" : day === "월" || day === "화" ? "done" : ""}
          >
            {day === "수" && <em>오늘</em>}
            {day}
          </span>
        ))}
      </div>

      <div className="week-actions" aria-label="기간 선택">
        <button type="button">오늘</button>
        <button type="button">이번 주</button>
      </div>
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
  if (subject === "국어") {
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

function LowerHeroCard({
  onStartLearning,
}: {
  onStartLearning: () => void;
}) {
  return (
    <article className="lower-hero-card">
      <div className="hero-copy">
        <span className="subject-name">국어</span>
        <h1>짧은 글 읽기</h1>
        <p>그림을 보고 주인공의 마음을 골라볼까요</p>
        <small>1학년 1학기 · 읽기 1차시</small>
      </div>

      <div className="story-illustration" aria-hidden="true">
        <div className="story-sky" />
        <div className="story-book">
          <span>마음</span>
          <span>고르기</span>
        </div>
        <div className="story-character">
          <span className="face-eye left" />
          <span className="face-eye right" />
          <span className="face-mouth" />
        </div>
      </div>

      <button
        type="button"
        className="primary-study-button"
        onClick={onStartLearning}
      >
        <span aria-hidden="true">▶</span>
        학습시작
      </button>
    </article>
  );
}

function UpperSubjectCards({
  onStartLearning,
}: {
  onStartLearning: () => void;
}) {
  const cards = [
    {
      title: "개념별따기",
      subtitle: "국어, 사회",
      tone: "green",
      action: "개념 보기",
      zoneId: "subject-korean" as const,
    },
    {
      title: "수학",
      subtitle: "비율과 비례식",
      tone: "blue",
      action: "단계별로 풀기",
      zoneId: "subject-math" as const,
    },
    {
      title: "과학",
      subtitle: "단원평가",
      tone: "mint",
      action: "복습하기",
      zoneId: "subject-science" as const,
    },
    {
      title: "사회",
      subtitle: "옛날 사람들의 놀이",
      tone: "white",
      action: "학습하기",
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
            <em>{card.action}</em>
          </button>
        </InteractionZone>
      ))}
    </div>
  );
}

function SmartAllRightRail({
  caseId,
  studentName,
}: {
  caseId: DemoCaseId;
  studentName: string;
}) {
  const isUpper = caseId === "upper-math";

  return (
    <aside className="right-rail" aria-label="추천과 학습 도구">
      <p className="recommend-title">{studentName}님을 위한 추천</p>

      <InteractionZone
        id="recommended-book"
        label="추천 독서"
        type="recommendation"
      >
        <article className="book-card">
          <button type="button" className="rail-arrow left" aria-label="이전 추천">
            ‹
          </button>
          <div className="book-cover">
            <strong>{isUpper ? "마을의 일 년 살이" : "예절 바른 훈랑이"}</strong>
            <span>{isUpper ? "이번 주 추천" : "이번 주 독서"}</span>
          </div>
          <button type="button" className="rail-arrow right" aria-label="다음 추천">
            ›
          </button>
          <div className="pager" aria-hidden="true">
            <span className="active" />
            <span />
          </div>
        </article>
      </InteractionZone>

      <InteractionZone
        id="challenge-card"
        label="올도전"
        type="recommendation"
      >
        <article className="challenge-card">
          <div>
            <strong>올도전</strong>
            <span>나의 별 {isUpper ? "12,750" : "17,250"}</span>
          </div>
          <div className="treasure-box" aria-hidden="true">
            ?
          </div>
        </article>
      </InteractionZone>

      <div className="quick-menu" aria-label="빠른 메뉴">
        {[
          { id: "attendance" as const, label: "출석" },
          { id: "study-record" as const, label: "학습기록" },
          { id: "wrong-note" as const, label: "오답노트" },
        ].map((menu) => (
          <InteractionZone
            key={menu.id}
            id={menu.id}
            label={menu.label}
            type="quick-menu"
          >
            <button type="button">
              <span aria-hidden="true" />
              {menu.label}
            </button>
          </InteractionZone>
        ))}
      </div>
    </aside>
  );
}

function LearningScreen({
  caseId,
  isHelpOpen,
  isExitMoment,
  onOpenHelp,
  onComplete,
  onExit,
}: {
  caseId: DemoCaseId;
  isHelpOpen: boolean;
  isExitMoment: boolean;
  onOpenHelp: () => void;
  onComplete: () => void;
  onExit: () => void;
}) {
  const isUpper = caseId === "upper-math";

  return (
    <div className={`learning-screen ${isHelpOpen ? "with-panel" : ""}`}>
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
          <div>
            <span>{isUpper ? "수학 · 비율과 비례식" : "국어 · 짧은 글 읽기"}</span>
            <strong>{isUpper ? "2단원 준비학습" : "주인공 마음 고르기"}</strong>
          </div>
          <button type="button" onClick={onOpenHelp}>
            AI 도움
          </button>
        </div>

        {isUpper ? <UpperMathProblem /> : <LowerKoreanProblem />}

        {isExitMoment && (
          <div className="exit-toast">
            나가기 전, 지금 문제를 조금만 더 이어볼 수 있어요.
          </div>
        )}

        <div className="lesson-actions">
          <InteractionZone
            id="help-button"
            label="힌트 보기"
            type="primary-action"
          >
            <button
              type="button"
              className="secondary-action"
              onClick={onOpenHelp}
            >
              힌트 보기
            </button>
          </InteractionZone>
          <InteractionZone
            id="complete-button"
            label="채점하고 완료"
            type="primary-action"
          >
            <button type="button" className="primary-action" onClick={onComplete}>
              채점하고 완료
            </button>
          </InteractionZone>
        </div>
      </section>
    </div>
  );
}

function LowerKoreanProblem() {
  return (
    <InteractionZone
      id="problem-board"
      label="현재 문제"
      type="content"
      className="problem-zone"
    >
      <article className="problem-card korean-problem">
        <span className="problem-count">문제 1</span>
        <h1>민지는 친구에게 색연필을 빌려주었어요.</h1>
        <p>
          친구가 고맙다고 말하자 민지는 활짝 웃었어요. 민지는 어떤 마음일까요?
        </p>
        <div className="picture-question" aria-hidden="true">
          <div className="child-figure happy" />
          <div className="pencil-box" />
          <div className="child-figure friend" />
        </div>
        <div className="answer-grid">
          {["기뻐요", "화나요", "무서워요"].map((answer) => (
            <button key={answer} type="button">
              {answer}
            </button>
          ))}
        </div>
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
        <h1>비례식을 세워 빈칸에 알맞은 수를 구하세요.</h1>
        <p>
          주스 원액 2컵에 물 5컵을 섞습니다. 같은 맛으로 원액 6컵을 만들려면 물은
          몇 컵이 필요할까요?
        </p>
        <div className="ratio-board" aria-label="비율 문제 풀이 영역">
          <div>
            <span>원액</span>
            <strong>2</strong>
            <strong>6</strong>
          </div>
          <div>
            <span>물</span>
            <strong>5</strong>
            <strong>?</strong>
          </div>
        </div>
        <div className="equation-line">
          2 : 5 = 6 : <input aria-label="정답 입력" placeholder="?" />
        </div>
      </article>
    </InteractionZone>
  );
}

function CompletionScreen({
  caseId,
  isFinal,
  onFinish,
  onRestart,
}: {
  caseId: DemoCaseId;
  isFinal: boolean;
  onFinish: () => void;
  onRestart: () => void;
}) {
  const isUpper = caseId === "upper-math";

  return (
    <div className="completion-screen">
      <WeekStrip isUpper={isUpper} />
      <InteractionZone
        id="completion-card"
        label={isFinal ? "오늘 학습 마무리" : "단위 학습 완료"}
        type="content"
        className="completion-card"
        role="region"
        ariaLabel="학습 완료 화면"
      >
        <div className="complete-medal" aria-hidden="true">
          ✓
        </div>
        <span>{isFinal ? "오늘의 학습 마무리" : "단위 학습 완료"}</span>
        <h1>
          {isFinal
            ? "오늘 학습을 잘 마쳤어요"
            : isUpper
              ? "비율 문제를 끝냈어요"
              : "국어 활동을 끝냈어요"}
        </h1>
        <p>
          {isFinal
            ? "오답이 남아 있으면 코치가 짧게 복습을 도와줄 거예요."
            : "AI 코치가 다음 학습을 짧게 이어갈 수 있게 추천해 줄 거예요."}
        </p>

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

        <div className="completion-actions">
          <button type="button" className="secondary-action" onClick={onRestart}>
            홈으로
          </button>
          <button type="button" className="primary-action" onClick={onFinish}>
            오늘 마무리
          </button>
        </div>
      </InteractionZone>
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
