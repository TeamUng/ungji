import type { TextMessage as TextMessageType } from "@/types/chat";

type TextMessageProps = {
  message: TextMessageType;
};

export function TextMessage({ message }: TextMessageProps) {
  return <div className="coach-text-message">{message.content}</div>;
}
