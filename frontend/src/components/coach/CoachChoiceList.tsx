import type { ChoiceItem } from "@/types/chat";

type CoachChoiceListProps = {
  choices: ChoiceItem[];
  compact?: boolean;
  onChoice: (choice: ChoiceItem) => void;
};

export function CoachChoiceList({ choices, compact = false, onChoice }: CoachChoiceListProps) {
  return (
    <div className={compact ? "coach-choice-list compact" : "coach-choice-list"}>
      {choices.map((choice) => (
        <button key={choice.id} type="button" onClick={() => onChoice(choice)}>
          {choice.label}
        </button>
      ))}
    </div>
  );
}
