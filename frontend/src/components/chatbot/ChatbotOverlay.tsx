"use client";

import { useState } from "react";
import type { RefObject } from "react";
import type { SmartAllView } from "@/data/smartallMockData";
import { PorongOverlay } from "@/components/porong/PorongOverlay";
import styles from "@/components/smartall/SmartAllHome.module.css";

type ChatbotOverlayProps = {
  stageRef: RefObject<HTMLDivElement | null>;
  view: SmartAllView;
};

export function ChatbotOverlay({ stageRef, view }: ChatbotOverlayProps) {
  const [isBubbleOpen, setIsBubbleOpen] = useState(false);
  const message =
    view === "today"
      ? "필요하면 뽀롱쌤이 바로 도와줄게요."
      : "카드를 고르다가 막히면 뽀롱쌤을 불러주세요.";

  return (
    <div className={styles.chatbotOverlay} aria-label="AI 코치 오버레이">
      <PorongOverlay
        stageRef={stageRef}
        touchpoint={view === "today" ? "tp1" : "tp4"}
        state={view === "today" ? "welcome" : "idle"}
        showBubble={isBubbleOpen}
        bubbleText={message}
        onTap={() => setIsBubbleOpen((current) => !current)}
      />
    </div>
  );
}
