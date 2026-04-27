import { CoachChoiceList } from "@/components/coach/CoachChoiceList";
import type { ChatMessage, ChoiceItem, ChoicesMessage, TextMessage } from "@/types/chat";

type CoachFloatingBubbleProps = {
  messages: ChatMessage[];
  isLoading: boolean;
  onChoice: (choice: ChoiceItem) => void;
};

export function CoachFloatingBubble({
  messages,
  isLoading,
  onChoice,
}: CoachFloatingBubbleProps) {
  const lastText = [...messages].reverse().find((message): message is TextMessage => message.type === "text");
  const lastChoices = [...messages].reverse().find((message): message is ChoicesMessage => message.type === "choices");

  return (
    <div className="coach-bubble">
      <p>{isLoading ? "잠깐만 기다려줘..." : lastText?.content ?? "필요하면 코치를 눌러줘."}</p>
      {lastChoices ? <CoachChoiceList choices={lastChoices.items} onChoice={onChoice} compact /> : null}
    </div>
  );
}
