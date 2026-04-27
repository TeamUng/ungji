import { ChoicesMessage } from "@/components/messages/ChoicesMessage";
import { HintCardMessage } from "@/components/messages/HintCardMessage";
import { ImageCardMessage } from "@/components/messages/ImageCardMessage";
import { TextMessage } from "@/components/messages/TextMessage";
import type { ChatMessage, ChoiceItem } from "@/types/chat";

type MessageRendererProps = {
  message: ChatMessage;
  onChoice: (choice: ChoiceItem) => void;
};

export function MessageRenderer({ message, onChoice }: MessageRendererProps) {
  if (message.type === "user") {
    return <div className="user-message">{message.content}</div>;
  }

  if (message.type === "text") {
    return <TextMessage message={message} />;
  }

  if (message.type === "choices") {
    return <ChoicesMessage message={message} onChoice={onChoice} />;
  }

  if (message.type === "image_card") {
    return <ImageCardMessage message={message} />;
  }

  return <HintCardMessage message={message} />;
}
