import type { Touchpoint } from "@/types/chat";

type CoachDrawerHeaderProps = {
  touchpoint: Touchpoint;
  onClose: () => void;
};

const touchpointLabel: Record<Touchpoint, string> = {
  tp1: "오늘의 추천",
  tp2: "다음 학습 추천",
  tp3: "학습 붙잡기",
  tp4: "학습 도움",
  tp5: "마무리 안내",
};

export function CoachDrawerHeader({ touchpoint, onClose }: CoachDrawerHeaderProps) {
  return (
    <header className="coach-drawer-header">
      <div>
        <p>AI 학습코치</p>
        <h2>{touchpointLabel[touchpoint]}</h2>
      </div>
      <button type="button" onClick={onClose} aria-label="채팅창 닫기">
        닫기
      </button>
    </header>
  );
}
