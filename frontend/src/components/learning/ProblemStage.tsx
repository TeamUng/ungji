import { ProblemContent } from "@/components/learning/ProblemContent";
import type { LearningProblem } from "@/types/learning";

type ProblemStageProps = {
  problem: LearningProblem;
};

export function ProblemStage({ problem }: ProblemStageProps) {
  return (
    <section className="problem-stage">
      <ProblemContent problem={problem} />
    </section>
  );
}
