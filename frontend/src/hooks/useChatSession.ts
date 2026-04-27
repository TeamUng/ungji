import { useMemo, useState } from "react";
import { mockChatClient } from "@/api/mockChatClient";
import type {
  ChatMessage,
  ChatRequest,
  ChoiceItem,
  Touchpoint,
  UseCase,
} from "@/types/chat";
import type { StudentCase } from "@/types/learning";

function createThreadId() {
  if ("randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `thread-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useChatSession(studentCase: StudentCase) {
  const threadId = useMemo(createThreadId, [studentCase.id]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTouchpoint, setCurrentTouchpoint] = useState<Touchpoint>("tp1");
  const [currentUseCase, setCurrentUseCase] = useState<UseCase>("talk");

  async function requestCoach(
    touchpoint: Touchpoint,
    useCase: UseCase,
    message: ChatRequest["message"],
    appendUserMessage?: ChatMessage,
  ) {
    const shouldReplaceMessages = message.type === "init" && !appendUserMessage;

    setIsLoading(true);
    setCurrentTouchpoint(touchpoint);
    setCurrentUseCase(useCase);

    if (appendUserMessage) {
      setMessages((prev) => [...prev, appendUserMessage]);
    }

    try {
      const response = await mockChatClient(
        {
          thread_id: threadId,
          student_id: studentCase.studentId,
          use_case: useCase,
          current_touchpoint: touchpoint,
          message,
        },
        studentCase,
      );

      setMessages((prev) =>
        shouldReplaceMessages ? response.messages : [...prev, ...response.messages],
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function startTouchpoint(touchpoint: Touchpoint, useCase: UseCase) {
    setMessages([]);
    await requestCoach(touchpoint, useCase, { type: "init", content: "init" });
  }

  async function sendChoice(choice: ChoiceItem) {
    await requestCoach(
      currentTouchpoint,
      currentUseCase,
      { type: "choice", content: choice.id },
      { type: "user", content: choice.label },
    );
  }

  async function sendText(content: string) {
    await requestCoach(
      currentTouchpoint,
      currentUseCase,
      { type: "text", content },
      { type: "user", content },
    );
  }

  function clearMessages() {
    setMessages([]);
  }

  return {
    threadId,
    messages,
    isLoading,
    currentTouchpoint,
    startTouchpoint,
    sendChoice,
    sendText,
    clearMessages,
  };
}
