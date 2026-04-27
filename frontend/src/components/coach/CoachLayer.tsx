import { CoachAvatarButton } from "@/components/coach/CoachAvatarButton";
import { CoachDrawer } from "@/components/coach/CoachDrawer";
import { CoachFloatingBubble } from "@/components/coach/CoachFloatingBubble";
import type { CoachSurface } from "@/hooks/useCoachLayer";
import type { ChatMessage, ChoiceItem, Touchpoint } from "@/types/chat";

type CoachLayerProps = {
  surface: CoachSurface;
  touchpoint: Touchpoint;
  messages: ChatMessage[];
  isLoading: boolean;
  onAvatarClick?: () => void;
  onClose: () => void;
  onChoice: (choice: ChoiceItem) => void;
  onSendText: (content: string) => void;
};

export function CoachLayer({
  surface,
  touchpoint,
  messages,
  isLoading,
  onAvatarClick,
  onClose,
  onChoice,
  onSendText,
}: CoachLayerProps) {
  if (surface === "hidden") {
    return (
      <div className="coach-widget" aria-label="AI 코치">
        <CoachAvatarButton onClick={onAvatarClick} />
      </div>
    );
  }

  return (
    <div className="coach-widget" aria-label="AI 코치">
      {surface === "floating" ? (
        <CoachFloatingBubble messages={messages} isLoading={isLoading} onChoice={onChoice} />
      ) : null}
      {surface === "drawer" ? (
        <CoachDrawer
          touchpoint={touchpoint}
          messages={messages}
          isLoading={isLoading}
          onClose={onClose}
          onChoice={onChoice}
          onSendText={onSendText}
        />
      ) : null}
      <CoachAvatarButton onClick={onAvatarClick} />
    </div>
  );
}
