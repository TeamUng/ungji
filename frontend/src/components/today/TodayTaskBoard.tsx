import { TodayTaskCard } from "@/components/today/TodayTaskCard";
import type { Subject, TodayTask } from "@/types/learning";

type TodayTaskBoardProps = {
  tasks: TodayTask[];
  selectedSubject: Subject;
  onStartTask: (taskId: string) => void;
};

export function TodayTaskBoard({ tasks, selectedSubject, onStartTask }: TodayTaskBoardProps) {
  const boardTasks = [...tasks].sort((a, b) => {
    if (a.subject === selectedSubject && b.subject !== selectedSubject) {
      return -1;
    }

    if (a.subject !== selectedSubject && b.subject === selectedSubject) {
      return 1;
    }

    return 0;
  });

  return (
    <div className="mt-5 grid grid-cols-3 gap-4">
      {boardTasks.map((task) => (
        <TodayTaskCard key={task.id} task={task} onStartTask={onStartTask} />
      ))}
    </div>
  );
}
