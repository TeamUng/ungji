"use client";

import type {
  CSSProperties,
  PointerEvent as ReactPointerEvent,
  RefObject,
} from "react";
import { useRef, useState } from "react";
import styles from "@/components/smartall/SmartAllHome.module.css";

type Point = {
  x: number;
  y: number;
};

type DragState = {
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
  moved: boolean;
};

type DraggableChatbotProps = {
  stageRef: RefObject<HTMLDivElement | null>;
  initialPosition: Point;
  message: string;
};

const CHATBOT_WIDTH = 154;
const CHATBOT_HEIGHT = 174;
const SAFE_PADDING = 14;
const BOTTOM_SAFE_PADDING = 4;

export function DraggableChatbot({
  stageRef,
  initialPosition,
  message,
}: DraggableChatbotProps) {
  const [position, setPosition] = useState(initialPosition);
  const [isDragging, setIsDragging] = useState(false);
  const [isPressed, setIsPressed] = useState(false);
  const [showBubble, setShowBubble] = useState(false);
  const dragStateRef = useRef<DragState | null>(null);

  const handlePointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0) {
      return;
    }

    dragStateRef.current = {
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: position.x,
      startY: position.y,
      moved: false,
    };

    setIsPressed(true);
    setIsDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const dragState = dragStateRef.current;
    const stage = stageRef.current;

    if (!dragState || !stage) {
      return;
    }

    const stageRect = stage.getBoundingClientRect();
    const scaleX = 1280 / stageRect.width;
    const scaleY = 800 / stageRect.height;
    const deltaX = (event.clientX - dragState.startClientX) * scaleX;
    const deltaY = (event.clientY - dragState.startClientY) * scaleY;
    const nextX = clamp(
      dragState.startX + deltaX,
      SAFE_PADDING,
      1280 - CHATBOT_WIDTH - SAFE_PADDING,
    );
    const nextY = clamp(
      dragState.startY + deltaY,
      56,
      800 - CHATBOT_HEIGHT - BOTTOM_SAFE_PADDING,
    );

    if (Math.abs(deltaX) + Math.abs(deltaY) > 4) {
      dragState.moved = true;
    }

    setPosition({ x: nextX, y: nextY });
  };

  const handlePointerEnd = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const dragState = dragStateRef.current;

    if (!dragState) {
      return;
    }

    event.currentTarget.releasePointerCapture(dragState.pointerId);
    setIsPressed(false);
    setIsDragging(false);

    window.setTimeout(() => {
      dragStateRef.current = null;
    }, 0);
  };

  const handleClick = () => {
    if (dragStateRef.current?.moved) {
      return;
    }

    setShowBubble((current) => !current);
  };

  const chatbotStyle: CSSProperties = {
    left: `${(position.x / 1280) * 100}%`,
    top: `${(position.y / 800) * 100}%`,
  };

  return (
    <aside
      className={`${styles.draggableChatbot} ${
        isDragging ? styles.draggingChatbot : ""
      } ${isPressed ? styles.pressedChatbot : ""}`}
      style={chatbotStyle}
    >
      {showBubble && <p className={styles.chatbotBubble}>{message}</p>}
      <button
        type="button"
        className={styles.chatbotHandle}
        aria-label="AI 코치 캐릭터 드래그"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerEnd}
        onPointerCancel={handlePointerEnd}
        onClick={handleClick}
      >
        <span className={styles.chatbotFace}>
          <span className={styles.chatbotEyeLeft} />
          <span className={styles.chatbotEyeRight} />
          <span className={styles.chatbotMouth} />
        </span>
        <span className={styles.dragGrip}>⋮⋮</span>
      </button>
    </aside>
  );
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
