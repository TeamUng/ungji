import { CoachComposer } from "@/components/coach/CoachComposer";
import { CoachDrawerHeader } from "@/components/coach/CoachDrawerHeader";
import { CoachMessageList } from "@/components/coach/CoachMessageList";
import type { ChatMessage, ChoiceItem, Touchpoint } from "@/types/chat";

type CoachDrawerProps = {
  touchpoint: Touchpoint;
  messages: ChatMessage[];
  isLoading: boolean;
  onClose: () => void;
  onChoice: (choice: ChoiceItem) => void;
  onSendText: (content: string) => void;
};

export function CoachDrawer({
  touchpoint,
  messages,
  isLoading,
  onClose,
  onChoice,
  onSendText,
}: CoachDrawerProps) {
  return (
    <aside className="coach-drawer" aria-label="AI 코치 채팅창">
      <CoachDrawerHeader touchpoint={touchpoint} onClose={onClose} />
      <CoachMessageList messages={messages} isLoading={isLoading} onChoice={onChoice} />
      <CoachComposer onSendText={onSendText} disabled={isLoading} />
    </aside>
  );
}
