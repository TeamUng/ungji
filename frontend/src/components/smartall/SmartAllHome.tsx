"use client";

import { useEffect, useRef, useState } from "react";
import { ChatbotOverlay } from "@/components/chatbot/ChatbotOverlay";
import type { SmartAllMode, SmartAllView } from "@/data/smartallMockData";
import { SmartAllShell } from "./SmartAllShell";
import styles from "./SmartAllHome.module.css";

export type { SmartAllMode, SmartAllView } from "@/data/smartallMockData";

export type SmartAllHomeProps = {
  initialView: SmartAllView;
  initialMode: SmartAllMode;
  initialReference: boolean;
};

export function SmartAllHome({
  initialView,
  initialMode,
  initialReference,
}: SmartAllHomeProps) {
  const [view, setView] = useState<SmartAllView>(initialView);
  const [mode, setMode] = useState<SmartAllMode>(initialMode);
  const [showReference, setShowReference] = useState(initialReference);
  const [showDevPanel, setShowDevPanel] = useState(false);
  const stageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();

      if (key === "r") {
        setShowReference((current) => !current);
      }

      if (key === "m") {
        setMode((current) => (current === "rebuilt" ? "reference" : "rebuilt"));
      }

      if (key === "d") {
        setShowDevPanel((current) => !current);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <main className={styles.smartallPage}>
      <SmartAllShell
        refNode={stageRef}
        view={view}
        mode={mode}
        showReference={showReference}
        onViewChange={setView}
      >
        <ChatbotOverlay stageRef={stageRef} view={view} />
      </SmartAllShell>

      {showDevPanel && (
        <section className={styles.devPanel} aria-label="스마트올 개발용 화면 제어">
          <div className={styles.segmentedGroup}>
            <button
              type="button"
              className={view === "today" ? styles.activeDevButton : ""}
              onClick={() => setView("today")}
            >
              오늘의 학습
            </button>
            <button
              type="button"
              className={view === "ai-match" ? styles.activeDevButton : ""}
              onClick={() => setView("ai-match")}
            >
              AI맞춤
            </button>
          </div>

          <button
            type="button"
            className={showReference ? styles.activeDevButton : ""}
            onClick={() => setShowReference((current) => !current)}
          >
            R 비교
          </button>

          <div className={styles.segmentedGroup}>
            <button
              type="button"
              className={mode === "rebuilt" ? styles.activeDevButton : ""}
              onClick={() => setMode("rebuilt")}
            >
              rebuilt
            </button>
            <button
              type="button"
              className={mode === "reference" ? styles.activeDevButton : ""}
              onClick={() => setMode("reference")}
            >
              reference
            </button>
          </div>
        </section>
      )}
    </main>
  );
}
