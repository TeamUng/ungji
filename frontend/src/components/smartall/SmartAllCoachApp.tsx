"use client";

import type {
  FormEvent,
} from "react";
import { useEffect, useRef, useState } from "react";
import { PorongOverlay } from "@/components/porong/PorongOverlay";
import type {
  PorongBubbleAction,
  PorongOverlayState,
} from "@/components/porong/porongTypes";
import {
  demoCases,
  demoStepLabels,
  demoStudentOptions,
  getStepMessages,
  makeChatRequest,
  mockChatAdapter,
} from "@/lib/mock-chat";
import type {
  ChatAdapter,
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

const caseLabels: Record<DemoCaseId, string> = {
  "lower-korean": "1~2학년 국어",
  "upper-math": "5~6학년 수학",
};

const subjectsByCase: Record<DemoCaseId, string[]> = {
  "lower-korean": ["국어", "수학", "문해력", "한자"],
  "upper-math": ["개념별따기", "수학", "과학", "사회"],
};

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
  chatAdapter = mockChatAdapter,
}: SmartAllCoachAppProps) {
  const [caseId, setCaseId] = useState<DemoCaseId>(initialCaseId);
  const [stepId, setStepId] = useState<DemoStepId>("home");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [chatError, setChatError] = useState("");
  const tabletRef = useRef<HTMLDivElement | null>(null);
  const turnIdRef = useRef(0);
  const streamRunRef = useRef(0);

  const bubbleMessages = getStepMessages(caseId, stepId);
  const bubbleText = getTextMessageContent(bubbleMessages);
  const bubbleActions = getBubbleActions(bubbleMessages);
  const isUpper = caseId === "upper-math";
  const shouldShowBubble =
    !chatOpen && ["home", "complete", "exit", "finish"].includes(stepId);
  const activeTouchpoint = demoCases[caseId].touchpointByStep[stepId];
  const porongState = getPorongState({
    stepId,
    chatOpen,
    isStreaming,
    isUpper,
  });
  const showTeachBackInput =
    stepId === "help" && !isStreaming && isLastCoachTeachBackPrompt(chatTurns);

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
  };

  const openLearning = () => {
    stopCurrentStream();
    setStepId("learning");
    setChatOpen(false);
    setChatTurns([]);
  };

  const openHelpPanel = () => {
    startChatPanel("help");
  };

  const handleBubbleChoice = (label: string) => {
    if (stepId === "home") {
      openLearning();
      return;
    }

    if (stepId === "complete") {
      if (label.includes("마무리") || label.includes("여기까지")) {
        moveToStep("finish");
        return;
      }

      openLearning();
      return;
    }

    if (stepId === "exit") {
      if (label.includes("도움") || label.includes("힌트")) {
        startChatPanel("exit", label, "choice");
        return;
      }

      openLearning();
      return;
    }

    if (stepId === "finish") {
      if (label.includes("오답 복습")) {
        startChatPanel("finish", label, "choice");
        return;
      }

      moveToStep("home");
    }
  };

  const handleChatChoice = (label: string) => {
    if (isStreaming) {
      return;
    }

    if (label === "문제로 돌아가기" || label === "다시 풀기") {
      setChatOpen(false);
      return;
    }

    if (label === "풀고 완료") {
      moveToStep("complete");
      return;
    }

    void sendToAdapter({
      targetStepId: stepId,
      content: label,
      messageType: "choice",
      reset: false,
    });
  };

  const handleTeachBackSubmit = (content: string) => {
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
          bubbleText={bubbleText}
          bubbleActions={bubbleActions}
          onTap={openHelpPanel}
          onBubbleAction={handleBubbleChoice}
        />

        <ChatPanel
          isOpen={chatOpen}
          caseId={caseId}
          turns={chatTurns}
          isBusy={isStreaming}
          errorMessage={chatError}
          showTeachBackInput={showTeachBackInput}
          onClose={() => setChatOpen(false)}
          onChoice={handleChatChoice}
          onTextSubmit={handleTeachBackSubmit}
          onComplete={() => moveToStep(stepId === "finish" ? "home" : "complete")}
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

        <section className="study-zone" aria-label="오늘의 학습 카드">
          {isUpper ? (
            <UpperSubjectCards onStartLearning={onStartLearning} />
          ) : (
            <LowerHeroCard onStartLearning={onStartLearning} />
          )}
        </section>

        <SmartAllRightRail caseId={caseId} />
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
        <button
          key={subject}
          type="button"
          className={subject === activeSubject ? "active" : ""}
        >
          <span>{index + 1}</span>
          {subject}
        </button>
      ))}
    </aside>
  );
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
    },
    {
      title: "수학",
      subtitle: "비율과 비례식",
      tone: "blue",
      action: "단계별로 풀기",
    },
    {
      title: "과학",
      subtitle: "단원평가",
      tone: "mint",
      action: "복습하기",
    },
    {
      title: "사회",
      subtitle: "옛날 사람들의 놀이",
      tone: "white",
      action: "학습하기",
    },
  ];

  return (
    <div className="upper-card-grid">
      {cards.map((card) => (
        <button
          key={card.title}
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
      ))}
    </div>
  );
}

function SmartAllRightRail({ caseId }: { caseId: DemoCaseId }) {
  const isUpper = caseId === "upper-math";

  return (
    <aside className="right-rail" aria-label="추천과 학습 도구">
      <p className="recommend-title">김웅진님을 위한 추천</p>

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

      <article className="challenge-card">
        <div>
          <strong>올도전</strong>
          <span>나의 별 {isUpper ? "12,750" : "17,250"}</span>
        </div>
        <div className="treasure-box" aria-hidden="true">
          ?
        </div>
      </article>

      <div className="quick-menu" aria-label="빠른 메뉴">
        {["출석", "학습기록", "오답노트"].map((label) => (
          <button key={label} type="button">
            <span aria-hidden="true" />
            {label}
          </button>
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
          <button type="button" onClick={onExit}>
            나가기
          </button>
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
          <button
            type="button"
            className="secondary-action"
            onClick={onOpenHelp}
          >
            힌트 보기
          </button>
          <button type="button" className="primary-action" onClick={onComplete}>
            채점하고 완료
          </button>
        </div>
      </section>
    </div>
  );
}

function LowerKoreanProblem() {
  return (
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
  );
}

function UpperMathProblem() {
  return (
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
      <section className="completion-card" aria-label="학습 완료 화면">
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
      </section>
    </div>
  );
}

function ChatPanel({
  isOpen,
  caseId,
  turns,
  isBusy,
  errorMessage,
  showTeachBackInput,
  onClose,
  onChoice,
  onTextSubmit,
  onComplete,
}: {
  isOpen: boolean;
  caseId: DemoCaseId;
  turns: ChatTurn[];
  isBusy: boolean;
  errorMessage: string;
  showTeachBackInput: boolean;
  onClose: () => void;
  onChoice: (choiceLabel: string) => void;
  onTextSubmit: (content: string) => void;
  onComplete: () => void;
}) {
  const [teachBackText, setTeachBackText] = useState("");
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const latestChoiceTurnId = findLatestChoiceTurnId(turns);

  useEffect(() => {
    const messageBox = messagesRef.current;

    if (!messageBox) {
      return;
    }

    messageBox.scrollTo({
      top: messageBox.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, isBusy, errorMessage]);

  const handleTeachBackSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onTextSubmit(teachBackText);
    setTeachBackText("");
  };

  return (
    <aside className={`chat-panel ${isOpen ? "is-open" : ""}`} aria-label="AI 코치 채팅창">
      <header>
        <div>
          <span>AI 학습코치</span>
          <strong>{caseLabels[caseId]}</strong>
        </div>
        <button type="button" aria-label="채팅창 닫기" onClick={onClose}>
          ×
        </button>
      </header>

      <div ref={messagesRef} className="chat-messages">
        {turns.map((turn) =>
          turn.role === "student" ? (
            <p key={turn.id} className="chat-student">
              {turn.content}
            </p>
          ) : (
            <MessageRenderer
              key={turn.id}
              message={turn.message}
              isChoiceActive={!isBusy && turn.id === latestChoiceTurnId}
              onChoice={onChoice}
            />
          ),
        )}

        {isBusy && <p className="chat-loading">코치가 생각하고 있어요...</p>}
        {errorMessage && <p className="chat-error">{errorMessage}</p>}
      </div>

      <footer className={showTeachBackInput ? "teachback-footer" : ""}>
        {showTeachBackInput ? (
          <form className="teachback-form" onSubmit={handleTeachBackSubmit}>
            <input
              value={teachBackText}
              onChange={(event) => setTeachBackText(event.target.value)}
              placeholder="예: 원액이 3배라 물도 3배예요"
              aria-label="내 말로 설명하기"
            />
            <button type="submit" className="primary-action" disabled={isBusy}>
              보내기
            </button>
          </form>
        ) : (
          <>
            <button type="button" className="secondary-action" onClick={onClose}>
              문제로 돌아가기
            </button>
            <button type="button" className="primary-action" onClick={onComplete}>
              풀고 완료
            </button>
          </>
        )}
      </footer>
    </aside>
  );
}

function MessageRenderer({
  message,
  isChoiceActive,
  onChoice,
}: {
  message: ResponseMessage;
  isChoiceActive: boolean;
  onChoice: (choiceLabel: string) => void;
}) {
  if (message.type === "text") {
    return <p className="chat-text">{message.content}</p>;
  }

  if (message.type === "choices") {
    return (
      <div className="chat-choice-list">
        {message.items.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={!isChoiceActive}
            onClick={() => onChoice(item.label)}
          >
            {item.label}
          </button>
        ))}
      </div>
    );
  }

  if (message.type === "image_card") {
    return (
      <article className="chat-image-card">
        <div className={`mock-image ${message.image_url}`} aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <p>{message.caption}</p>
      </article>
    );
  }

  return (
    <article className="hint-card">
      {message.steps.map((step) => (
        <div key={step.step}>
          <span>{step.step}</span>
          <p>{step.content}</p>
        </div>
      ))}
    </article>
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

function findLatestChoiceTurnId(turns: ChatTurn[]) {
  return [...turns]
    .reverse()
    .find((turn) => turn.role === "coach" && turn.message.type === "choices")
    ?.id;
}

function isLastCoachTeachBackPrompt(turns: ChatTurn[]) {
  const lastCoachText = [...turns]
    .reverse()
    .find((turn) => turn.role === "coach" && turn.message.type === "text");

  return (
    lastCoachText?.role === "coach" &&
    lastCoachText.message.type === "text" &&
    lastCoachText.message.content.includes("네 말로")
  );
}
