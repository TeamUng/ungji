import { useState } from "react";
import type { LearningProblem } from "@/types/learning";

type AnswerAreaProps = {
  problem: LearningProblem;
};

export function AnswerArea({ problem }: AnswerAreaProps) {
  const [selectedChoiceId, setSelectedChoiceId] = useState<string | null>(null);
  const selectedChoice = problem.choices.find((choice) => choice.id === selectedChoiceId);

  return (
    <section className="answer-area">
      <div className="answer-options">
        {problem.choices.map((choice) => (
          <button
            className={choice.id === selectedChoiceId ? "answer-option active" : "answer-option"}
            key={choice.id}
            type="button"
            onClick={() => setSelectedChoiceId(choice.id)}
          >
            {choice.label}
          </button>
        ))}
      </div>
      <div className="answer-feedback">
        {selectedChoice ? (
          <>
            <p>선택한 답: {selectedChoice.label}</p>
            <strong>코치 힌트</strong>
            <span>{problem.hint}</span>
          </>
        ) : (
          <p>답을 고르거나, 오른쪽 아래 코치를 눌러 도움을 받아보세요.</p>
        )}
      </div>
    </section>
  );
}
