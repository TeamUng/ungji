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
  const fallbackChoices =
    task.subject === "국어"
      ? [
          { id: "first", label: "처음 문장" },
          { id: "middle", label: "가운데 문장" },
          { id: "last", label: "마지막 문장" },
        ]
      : [
          { id: "choice-a", label: "보기 1" },
          { id: "choice-b", label: "보기 2" },
          { id: "choice-c", label: "보기 3" },
        ];

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
          choices: fallbackChoices,
          answerLabel: fallbackChoices[0].label,
          hint: "막히면 답 보기 대신 오른쪽 아래 코치 캐릭터를 눌러 도움을 받을 수 있어요.",
        };

  return (
    <LearningContentShell
      title={task.title}
      subtitle={`${studentCase.studentName} · ${task.subject} · ${task.unit}`}
      onBackToday={onBackToday}
    >
      <div className="learning-actions" aria-label="터치포인트 시연 컨트롤">
        <button
          type="button"
          onClick={onExitAttempt}
          title="실제 서비스에서는 학생의 뒤로가기, 닫기, 이탈 행동을 감지했을 때 발생하는 TP3 시연입니다."
        >
          시연: 이탈 감지
        </button>
        <button
          type="button"
          onClick={onCompleteTask}
          title="단위 학습 완료 후 다음 학습을 추천하는 TP2 시연입니다."
        >
          시연: 단위 완료
        </button>
        <button
          type="button"
          onClick={onFinishDay}
          title="오늘 학습 종료 시 오답 복습 또는 마무리를 안내하는 TP5 시연입니다."
        >
          시연: 하루 종료
        </button>
      </div>
      <ProblemStage problem={problem} />
      <AnswerArea problem={problem} />
    </LearningContentShell>
  );
}
