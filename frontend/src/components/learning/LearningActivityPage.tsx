import { AnswerArea } from "@/components/learning/AnswerArea";
import { LearningContentShell } from "@/components/learning/LearningContentShell";
import { ProblemStage } from "@/components/learning/ProblemStage";
import type { LearningProblem, StudentCase, TodayTask } from "@/types/learning";

type LearningActivityPageProps = {
  studentCase: StudentCase;
  task: TodayTask;
  onBackToday: () => void;
  onCompleteTask: () => void;
  onExitAttempt: () => void;
  onFinishDay: () => void;
};

export function LearningActivityPage({
  studentCase,
  task,
  onBackToday,
  onCompleteTask,
  onExitAttempt,
  onFinishDay,
}: LearningActivityPageProps) {
  const problem: LearningProblem =
    task.id === studentCase.problem.taskId
      ? studentCase.problem
      : {
          ...studentCase.problem,
          id: `problem-${task.id}`,
          taskId: task.id,
          subject: task.subject,
          title: task.title,
          prompt: `${task.description} 지금은 시연용 문제 화면이므로 오른쪽 아래 코치 도움 흐름을 확인할 수 있어요.`,
          choices: [
            { id: "try", label: "한 번 해볼게요" },
            { id: "help", label: "코치 도움 받기" },
          ],
          answerLabel: "한 번 해볼게요",
          hint: "시연에서는 추천 학습을 중심으로 AI 코치 흐름을 확인합니다.",
        };

  return (
    <LearningContentShell
      title={task.title}
      subtitle={`${studentCase.studentName} · ${task.subject} · ${task.unit}`}
      onBackToday={onBackToday}
    >
      <ProblemStage problem={problem} />
      <AnswerArea problem={problem} />
      <div className="learning-actions" aria-label="터치포인트 시연 버튼">
        <button type="button" onClick={onExitAttempt}>
          나가려 해요
        </button>
        <button type="button" onClick={onCompleteTask}>
          학습 완료
        </button>
        <button type="button" onClick={onFinishDay}>
          오늘 끝내기
        </button>
      </div>
    </LearningContentShell>
  );
}
