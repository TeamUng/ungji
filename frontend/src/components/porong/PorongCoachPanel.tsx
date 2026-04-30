"use client";

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import type {
  ChatTurn,
  ResponseMessage,
} from "@/types/chat";

type PorongCoachPanelProps = {
  isOpen: boolean;
  title: string;
  turns: ChatTurn[];
  isBusy: boolean;
  errorMessage: string;
  showTeachBackInput: boolean;
  onClose: () => void;
  onChoice: (choiceLabel: string) => void;
  onTextSubmit: (content: string) => void;
  onComplete: () => void;
};

export function PorongCoachPanel({
  isOpen,
  title,
  turns,
  isBusy,
  errorMessage,
  showTeachBackInput,
  onClose,
  onChoice,
  onTextSubmit,
  onComplete,
}: PorongCoachPanelProps) {
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
          <strong>{title}</strong>
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

function findLatestChoiceTurnId(turns: ChatTurn[]) {
  return [...turns]
    .reverse()
    .find((turn) => turn.role === "coach" && turn.message.type === "choices")
    ?.id;
}
