import { CaseSelector } from "@/components/dev/CaseSelector";
import type { CaseId } from "@/types/learning";

type SmartAllTopBarProps = {
  activeCaseId: CaseId;
  onCaseChange: (caseId: CaseId) => void;
};

export function SmartAllTopBar({
  activeCaseId,
  onCaseChange,
}: SmartAllTopBarProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between bg-[#161d25] px-5 text-white">
      <div className="flex items-center gap-3">
        <div className="grid h-9 w-9 place-items-center rounded-full bg-white/10 text-sm font-bold">
          W
        </div>
        <div>
          <p className="text-xs text-white/60">AI 학습코치 데모</p>
          <h1 className="text-base font-bold">오늘의 학습</h1>
        </div>
      </div>
      <nav className="hidden items-center gap-7 text-sm font-semibold text-white/70 lg:flex">
        <span className="text-white">오늘의 학습</span>
        <span>AI학습</span>
        <span>단원평가</span>
        <span>학습시간</span>
      </nav>
      <div className="topbar-actions">
        <CaseSelector activeCaseId={activeCaseId} onCaseChange={onCaseChange} />
        <span className="rounded-full bg-white px-4 py-2 text-xs font-bold text-slate-900">
          ay-front
        </span>
      </div>
    </header>
  );
}
