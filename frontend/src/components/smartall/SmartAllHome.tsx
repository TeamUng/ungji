"use client";

import { useRef, useState } from "react";
import { InteractionZoneProvider } from "@/components/chatbot/InteractionZoneProvider";
import { PorongOverlay } from "@/components/porong/PorongOverlay";
import type { PorongPoint } from "@/components/porong/porongTypes";
import type { SmartAllMode, SmartAllView } from "@/data/smartallMockData";
import { DateSelector } from "./DateSelector";
import { MainLearningCard } from "./MainLearningCard";
import { RightSidebar } from "./RightSidebar";
import { SubjectRail } from "./SubjectRail";
import { TopHeader } from "./TopHeader";
import styles from "./SmartAllHome.module.css";

export type { SmartAllMode, SmartAllView } from "@/data/smartallMockData";

const PORONG_POSITION_STORAGE_KEY = "ungji-smartall-porong-position";

export type SmartAllHomeProps = {
  initialView?: SmartAllView;
  initialMode?: SmartAllMode;
  initialReference?: boolean;
};

export function SmartAllHome({
  initialView = "today",
  initialMode = "rebuilt",
  initialReference = false,
}: SmartAllHomeProps) {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [porongPosition, setPorongPosition] = useState<PorongPoint | null>(() =>
    readSavedPorongPosition(),
  );

  const savePorongPosition = (position: PorongPoint) => {
    setPorongPosition(position);

    try {
      window.localStorage.setItem(
        PORONG_POSITION_STORAGE_KEY,
        JSON.stringify(position),
      );
    } catch {
      // 저장 공간 접근이 막혀도 드래그와 학습 화면은 그대로 동작해야 합니다.
    }
  };

  return (
    <InteractionZoneProvider>
      <main className={styles.smartallPage}>
        <section
          ref={stageRef}
          className={styles.smartallStage}
          aria-label="스마트올 홈 화면과 AI 코치 오버레이"
          data-initial-view={initialView}
          data-initial-mode={initialMode}
          data-reference-enabled={initialReference ? "true" : "false"}
        >
          <div className={styles.staticSmartAllLayout}>
            <TopHeader />
            <DateSelector />

            <div className={styles.contentGrid}>
              <SubjectRail />
              <MainLearningCard />
              <RightSidebar />
            </div>
          </div>

          <PorongOverlay
            stageRef={stageRef}
            touchpoint="tp1"
            state="welcome"
            initialPosition={porongPosition}
            showBubble
            bubbleText="필요하면 나를 끌어다 놓아봐!"
            onDragEnd={savePorongPosition}
          />
        </section>
      </main>
    </InteractionZoneProvider>
  );
}

function readSavedPorongPosition(): PorongPoint | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const saved = window.localStorage.getItem(PORONG_POSITION_STORAGE_KEY);

    if (!saved) {
      return null;
    }

    const parsed = JSON.parse(saved) as Partial<PorongPoint>;

    if (typeof parsed.x !== "number" || typeof parsed.y !== "number") {
      return null;
    }

    return {
      x: parsed.x,
      y: parsed.y,
    };
  } catch {
    return null;
  }
}
