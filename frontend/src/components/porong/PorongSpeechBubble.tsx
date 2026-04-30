import type {
  PorongBubbleAction,
} from "@/components/porong/porongTypes";
import { FormattedText } from "./FormattedText";

type PorongSpeechBubbleProps = {
  eyebrow?: string;
  text?: string;
  actions?: PorongBubbleAction[];
  onAction?: (action: PorongBubbleAction) => void;
};

export function PorongSpeechBubble({
  eyebrow,
  text,
  actions = [],
  onAction,
}: PorongSpeechBubbleProps) {
  if (!text && actions.length === 0) {
    return null;
  }

  return (
    <aside className="porong-speech-bubble" aria-label="뽀롱쌤 안내 말풍선">
      {eyebrow && <span className="porong-touchpoint-chip">{eyebrow}</span>}
      {text && (
        <p>
          <FormattedText text={text} />
        </p>
      )}
      {actions.length > 0 && (
        <div className="porong-bubble-actions">
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={() => onAction?.(action)}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </aside>
  );
}
