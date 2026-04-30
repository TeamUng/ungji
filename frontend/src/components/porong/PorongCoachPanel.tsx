"use client";

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import type {
  ChatTurn,
  ChoiceSelection,
  ResponseMessage,
} from "@/types/chat";
import { FormattedText } from "./FormattedText";

type PorongCoachPanelProps = {
  isOpen: boolean;
  turns: ChatTurn[];
  isBusy: boolean;
  errorMessage: string;
  onClose: () => void;
  onChoice: (choice: ChoiceSelection) => void;
  onTextSubmit: (content: string) => void;
};

export function PorongCoachPanel({
  isOpen,
  turns,
  isBusy,
  errorMessage,
  onClose,
  onChoice,
  onTextSubmit,
}: PorongCoachPanelProps) {
  const [replyText, setReplyText] = useState("");
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

  const handleReplySubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = replyText.trim();
    if (!trimmed || isBusy) {
      return;
    }

    onTextSubmit(trimmed);
    setReplyText("");
  };

  return (
    <aside className={`chat-panel ${isOpen ? "is-open" : ""}`} aria-label="맞춤 학습 코치 채팅창">
      <header>
        <div>
          <strong>맞춤 학습 코치</strong>
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

      <footer>
        <form className="chat-reply-form" onSubmit={handleReplySubmit}>
          <input
            value={replyText}
            onChange={(event) => setReplyText(event.target.value)}
            placeholder="답장을 입력해 주세요"
            aria-label="코치에게 답장하기"
          />
          <button
            type="submit"
            className="primary-action"
            disabled={isBusy || replyText.trim() === ""}
          >
            보내기
          </button>
        </form>
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
  onChoice: (choice: ChoiceSelection) => void;
}) {
  if (message.type === "text") {
    return (
      <p className="chat-text">
        <FormattedText text={message.content} />
      </p>
    );
  }

  if (message.type === "choices") {
    return (
      <div className="chat-choice-list">
        {message.items.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={!isChoiceActive}
            onClick={() => onChoice(item)}
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
        <p>
          <FormattedText text={message.caption} />
        </p>
      </article>
    );
  }

  return (
    <article className="hint-card">
      {message.steps.map((step) => (
        <div key={step.step}>
          <span>{step.step}</span>
          <p>
            <FormattedText text={step.content} />
          </p>
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
