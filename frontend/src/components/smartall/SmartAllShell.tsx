import type { ReactNode, RefObject } from "react";
import type { SmartAllMode, SmartAllView } from "@/data/smartallMockData";
import { referenceImages } from "@/data/smartallMockData";
import { AIMatchGridView } from "./AIMatchGridView";
import { ReferenceBackground } from "./ReferenceBackground";
import { TodayLearningView } from "./TodayLearningView";
import { TopNav } from "./TopNav";
import { WeekSelector } from "./WeekSelector";
import styles from "./SmartAllHome.module.css";

type SmartAllShellProps = {
  refNode: RefObject<HTMLDivElement | null>;
  view: SmartAllView;
  mode: SmartAllMode;
  showReference: boolean;
  onViewChange: (view: SmartAllView) => void;
  children: ReactNode;
};

export function SmartAllShell({
  refNode,
  view,
  mode,
  showReference,
  onViewChange,
  children,
}: SmartAllShellProps) {
  const isReferenceMode = mode === "reference";
  const themeClass = view === "today" ? styles.themeToday : styles.themeAi;

  return (
    <section
      ref={refNode}
      className={`${styles.smartallStage} ${themeClass}`}
      aria-label="스마트올 홈 배경 UI"
    >
      {isReferenceMode ? (
        <ReferenceBackground image={referenceImages[view]} opacity={1} />
      ) : (
        <div className={styles.rebuiltLayer}>
          <TopNav activeView={view} onViewChange={onViewChange} />
          <main className={styles.homeCanvas}>
            <WeekSelector view={view} />
            {view === "today" ? <TodayLearningView /> : <AIMatchGridView />}
          </main>
        </div>
      )}

      {!isReferenceMode && showReference && (
        <ReferenceBackground
          image={referenceImages[view]}
          opacity={0.4}
          isOverlay
        />
      )}

      {children}
    </section>
  );
}
