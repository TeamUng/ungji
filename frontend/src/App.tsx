type TodayTask = {
  id: string;
  subject: string;
  title: string;
  minutes: number;
  status: "recommended" | "ready" | "done";
};

const todayTasks: TodayTask[] = [
  {
    id: "math-ratio",
    subject: "수학",
    title: "비율 개념을 한 문제로 정리하기",
    minutes: 8,
    status: "recommended",
  },
  {
    id: "korean-reading",
    subject: "국어",
    title: "짧은 글 읽고 마음 고르기",
    minutes: 6,
    status: "ready",
  },
  {
    id: "social-review",
    subject: "사회",
    title: "어제 배운 핵심 낱말 복습",
    minutes: 5,
    status: "ready",
  },
];

const subjects = ["수학", "국어", "사회", "영어"];

function App() {
  return (
    <main className="min-h-screen bg-[#eef3f8] px-4 py-5 text-slate-950 sm:px-6 lg:px-8">
      <section className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-7xl items-center justify-center">
        <div className="tablet-shell">
          <header className="flex h-14 items-center justify-between bg-[#161d25] px-5 text-white">
            <div className="flex items-center gap-3">
              <div className="grid h-9 w-9 place-items-center rounded-full bg-white/10 text-sm font-bold">
                W
              </div>
              <div>
                <p className="text-xs text-white/60">AI 학습코치 데모</p>
                <h1 className="text-base font-bold">오늘의 학습</h1>
              </div>
            </div>
            <nav className="hidden items-center gap-7 text-sm font-semibold text-white/70 md:flex">
              <span className="text-white">오늘의 학습</span>
              <span>AI학습</span>
              <span>단원평가</span>
              <span>학습시간</span>
            </nav>
            <span className="rounded-full bg-white px-4 py-2 text-xs font-bold text-slate-900">
              ay-front
            </span>
          </header>

          <div className="relative grid flex-1 grid-cols-[168px_minmax(0,1fr)] overflow-hidden bg-[#f9e78e]">
            <aside className="bg-white/92 px-4 py-8 shadow-[16px_0_36px_rgba(15,23,42,0.08)]">
              <p className="mb-4 text-xs font-bold text-slate-500">과목</p>
              <div className="space-y-3">
                {subjects.map((subject) => (
                  <button
                    className={`subject-button ${
                      subject === "수학" ? "subject-button-active" : ""
                    }`}
                    key={subject}
                    type="button"
                  >
                    {subject}
                  </button>
                ))}
              </div>
            </aside>

            <section className="grid min-w-0 grid-cols-[minmax(0,1fr)_280px] gap-5 p-6">
              <div className="min-w-0">
                <div className="mb-5 flex items-center justify-between rounded-full bg-white/90 px-5 py-3 shadow-sm">
                  <div>
                    <p className="text-xs font-bold text-slate-500">4월 28일 화요일</p>
                    <p className="text-lg font-extrabold">오늘 배정된 학습 3개</p>
                  </div>
                  <div className="flex gap-2">
                    {["월", "화", "수", "목", "금"].map((day) => (
                      <span
                        className={`day-chip ${day === "화" ? "day-chip-active" : ""}`}
                        key={day}
                      >
                        {day}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="hero-card">
                  <div className="max-w-md">
                    <p className="mb-3 text-sm font-extrabold text-sky-100">추천 학습</p>
                    <h2 className="text-4xl font-black text-white">수학</h2>
                    <p className="mt-4 max-w-sm text-lg font-bold leading-8 text-white/90">
                      비율이 헷갈릴 때는 한 문제를 단계별로 나누면 훨씬 쉬워져요.
                    </p>
                  </div>
                  <div className="absolute bottom-8 right-8 hidden h-28 w-64 rounded-[32px] bg-white/18 ring-1 ring-white/20 md:block" />
                </div>

                <div className="mt-5 grid grid-cols-3 gap-4">
                  {todayTasks.map((task) => (
                    <article className="task-card" key={task.id}>
                      <div className="flex items-center justify-between gap-3">
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
                          {task.subject}
                        </span>
                        <span className="text-xs font-bold text-slate-400">
                          {task.minutes}분
                        </span>
                      </div>
                      <h3 className="mt-4 text-base font-extrabold leading-6 text-slate-950">
                        {task.title}
                      </h3>
                      <button className="mt-5 w-full rounded-xl bg-slate-950 px-3 py-3 text-sm font-bold text-white transition hover:bg-slate-800">
                        시작하기
                      </button>
                    </article>
                  ))}
                </div>
              </div>

              <aside className="hidden rounded-[28px] bg-white/58 p-4 shadow-sm ring-1 ring-white/60 lg:block">
                <p className="mb-3 text-sm font-extrabold text-slate-700">
                  검토 포인트
                </p>
                <div className="space-y-3 text-sm font-semibold leading-6 text-slate-700">
                  <p>FE1: Vite 앱 세팅</p>
                  <p>FE2: 케이스 목업 데이터</p>
                  <p>FE3: 오늘의 학습 화면</p>
                  <p>FE5: AI 코치 레이어</p>
                </div>
              </aside>
            </section>

            <div className="coach-widget" aria-label="AI 코치 추천">
              <div className="coach-bubble">
                <p>오늘은 수학부터 해볼까?</p>
                <button type="button">수학으로 이동하기</button>
              </div>
              <button className="coach-face" type="button" aria-label="AI 코치 열기">
                <img src="/assets/coach-avatar.svg" alt="" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

export default App;
