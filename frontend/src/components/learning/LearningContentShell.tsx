import type { PropsWithChildren } from "react";

type LearningContentShellProps = PropsWithChildren<{
  title: string;
  subtitle: string;
  onBackToday: () => void;
}>;

export function LearningContentShell({
  title,
  subtitle,
  onBackToday,
  children,
}: LearningContentShellProps) {
  return (
    <section className="learning-shell">
      <div className="learning-header">
        <div>
          <p>{subtitle}</p>
          <h2>{title}</h2>
        </div>
        <button type="button" onClick={onBackToday}>
          오늘의 학습
        </button>
      </div>
      <div className="learning-body">{children}</div>
    </section>
  );
}
