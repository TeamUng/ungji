import { MessageRenderer } from "@/components/messages/MessageRenderer";
import type { ChatMessage, ChoiceItem } from "@/types/chat";

type CoachMessageListProps = {
  messages: ChatMessage[];
  isLoading: boolean;
  onChoice: (choice: ChoiceItem) => void;
};

export function CoachMessageList({ messages, isLoading, onChoice }: CoachMessageListProps) {
  return (
    <div className="coach-message-list">
      {messages.map((message, index) => (
        <MessageRenderer
          key={`${message.type}-${index}`}
          message={message}
          onChoice={onChoice}
        />
      ))}
      {isLoading ? <div className="message-loading">코치가 생각하고 있어요...</div> : null}
    </div>
  );
}
