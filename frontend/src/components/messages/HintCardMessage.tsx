import type { HintCardMessage as HintCardMessageType } from "@/types/chat";

type HintCardMessageProps = {
  message: HintCardMessageType;
};

export function HintCardMessage({ message }: HintCardMessageProps) {
  return (
    <div className="hint-card-message">
      {message.steps.map((step) => (
        <div className="hint-step" key={step.step}>
          <span>{step.step}</span>
          <p>{step.content}</p>
        </div>
      ))}
    </div>
  );
}
