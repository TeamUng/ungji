import { CoachChoiceList } from "@/components/coach/CoachChoiceList";
import type { ChoiceItem, ChoicesMessage as ChoicesMessageType } from "@/types/chat";

type ChoicesMessageProps = {
  message: ChoicesMessageType;
  onChoice: (choice: ChoiceItem) => void;
};

export function ChoicesMessage({ message, onChoice }: ChoicesMessageProps) {
  return <CoachChoiceList choices={message.items} onChoice={onChoice} />;
}
