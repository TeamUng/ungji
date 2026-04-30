import type {
  PorongBubbleAction,
  PorongTouchpoint,
} from "@/components/porong/porongTypes";

type PorongSpeechBubbleProps = {
  touchpoint?: PorongTouchpoint;
  eyebrow?: string;
  text?: string;
  actions?: PorongBubbleAction[];
  onAction?: (label: string) => void;
};

export function PorongSpeechBubble({
  touchpoint,
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
      {(eyebrow || touchpoint) && (
        <span className="porong-touchpoint-chip">
          {eyebrow ?? touchpoint?.toUpperCase()}
        </span>
      )}
      {text && <p>{text}</p>}
      {actions.length > 0 && (
        <div className="porong-bubble-actions">
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={() => onAction?.(action.label)}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </aside>
  );
}
