import type { TodayTask } from "@/types/learning";

type TodayTaskCardProps = {
  task: TodayTask;
  onStartTask: (taskId: string) => void;
};

export function TodayTaskCard({ task, onStartTask }: TodayTaskCardProps) {
  return (
    <article className="task-card">
      <div className="flex items-center justify-between gap-3">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
          {task.subject}
        </span>
        <span className="text-xs font-bold text-slate-400">{task.minutes}분</span>
      </div>
      <h3 className="mt-4 text-base font-extrabold leading-6 text-slate-950">{task.title}</h3>
      <p className="task-card-description mt-2 text-sm font-semibold leading-6 text-slate-500">
        {task.unit} · 난이도 {task.difficulty}
      </p>
      <button
        className="mt-5 w-full rounded-xl bg-slate-950 px-3 py-3 text-sm font-bold text-white transition hover:bg-slate-800"
        type="button"
        onClick={() => onStartTask(task.id)}
      >
        시작하기
      </button>
    </article>
  );
}
