import type { LearningProblem } from "@/types/learning";

type ProblemContentProps = {
  problem: LearningProblem;
};

export function ProblemContent({ problem }: ProblemContentProps) {
  return (
    <>
      <div className="problem-copy">
        <p className="problem-kicker">{problem.subject} 문제</p>
        <h3>{problem.title}</h3>
        <p>{problem.prompt}</p>
      </div>
      <img src={problem.imageUrl} alt={problem.imageAlt} />
    </>
  );
}
