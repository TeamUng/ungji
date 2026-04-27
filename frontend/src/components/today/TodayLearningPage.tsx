import { useMemo, useState } from "react";
import { SubjectSidebar } from "@/components/today/SubjectSidebar";
import { TodayTaskBoard } from "@/components/today/TodayTaskBoard";
import type { Touchpoint } from "@/types/chat";
import type { StudentCase, Subject } from "@/types/learning";

type TodayLearningPageProps = {
  studentCase: StudentCase;
  onStartTask: (taskId: string) => void;
  onShowTouchpoint: (touchpoint: Touchpoint) => void;
};

export function TodayLearningPage({
  studentCase,
  onStartTask,
  onShowTouchpoint,
}: TodayLearningPageProps) {
  const [selectedSubject, setSelectedSubject] = useState<Subject>(
    studentCase.todayTasks[0]?.subject ?? "수학",
  );
  const subjects = useMemo(
    () => Array.from(new Set(studentCase.todayTasks.map((task) => task.subject))),
    [studentCase.todayTasks],
  );
  const recommendedTask =
    studentCase.todayTasks.find((task) => task.id === studentCase.recommendedTaskId) ??
    studentCase.todayTasks[0];

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[168px_minmax(0,1fr)] overflow-hidden">
      <SubjectSidebar
        subjects={subjects}
        selectedSubject={selectedSubject}
        onSelectSubject={setSelectedSubject}
      />

      <section className="grid min-w-0 grid-cols-[minmax(0,1fr)_286px] gap-5 p-6">
        <div className="min-w-0">
          <div className="mb-5 flex items-center justify-between rounded-full bg-white/90 px-5 py-3 shadow-sm">
            <div>
              <p className="text-xs font-bold text-slate-500">4월 28일 화요일</p>
              <p className="text-lg font-extrabold">
                {studentCase.studentName}의 오늘 학습 {studentCase.todayTasks.length}개
              </p>
            </div>
            <div className="flex gap-2">
              {["월", "화", "수", "목", "금"].map((day) => (
                <span className={`day-chip ${day === "화" ? "day-chip-active" : ""}`} key={day}>
                  {day}
                </span>
              ))}
            </div>
          </div>

          <div className="hero-card">
            <div className="max-w-md">
              <p className="mb-3 text-sm font-extrabold text-sky-100">추천 학습</p>
              <h2 className="text-4xl font-black text-white">{recommendedTask.subject}</h2>
              <p className="mt-4 max-w-sm text-lg font-bold leading-8 text-white/90">
                {recommendedTask.description}
              </p>
              <button
                className="mt-6 rounded-2xl bg-white px-5 py-3 text-sm font-black text-sky-700 shadow-sm"
                type="button"
                onClick={() => onStartTask(recommendedTask.id)}
              >
                추천 학습 시작
              </button>
            </div>
            <div className="hero-visual" aria-hidden="true" />
          </div>

          <TodayTaskBoard
            selectedSubject={selectedSubject}
            tasks={studentCase.todayTasks}
            onStartTask={onStartTask}
          />
        </div>

        <aside className="hidden rounded-[28px] bg-white/58 p-4 shadow-sm ring-1 ring-white/60 lg:block">
          <p className="mb-2 text-sm font-extrabold text-slate-700">학생 상태</p>
          <div className="space-y-3 text-sm font-semibold leading-6 text-slate-700">
            <p>{studentCase.gradeLabel} · {studentCase.segment}</p>
            <p>{studentCase.summary}</p>
            <p>AI 예상점수 {recommendedTask.aiPredictedScore}점</p>
          </div>
          <div className="mt-5 space-y-2">
            <button className="debug-action" type="button" onClick={() => onShowTouchpoint("tp1")}>
              TP1 추천 다시 보기
            </button>
            <button className="debug-action" type="button" onClick={() => onShowTouchpoint("tp5")}>
              TP5 종료 안내 보기
            </button>
          </div>
        </aside>
      </section>
    </div>
  );
}
