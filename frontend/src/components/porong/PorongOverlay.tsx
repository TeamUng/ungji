"use client";

import type { KeyboardEvent, RefObject } from "react";
import { useRef } from "react";
import { PorongMascot } from "./PorongMascot";
import { PorongSpeechBubble } from "./PorongSpeechBubble";
import type {
  PorongBubbleAction,
  PorongOverlayState,
  PorongSnapPoint,
  PorongTouchpoint,
} from "./porongTypes";
import { usePorongDrag } from "./usePorongDrag";

type PorongOverlayProps = {
  stageRef: RefObject<HTMLElement | null>;
  touchpoint?: PorongTouchpoint;
  state?: PorongOverlayState;
  defaultPosition?: PorongSnapPoint;
  chatOpen?: boolean;
  showBubble?: boolean;
  bubbleText?: string;
  bubbleActions?: PorongBubbleAction[];
  onTap?: () => void;
  onBubbleAction?: (label: string) => void;
  onDragEnd?: (snapPoint: PorongSnapPoint) => void;
};

export function PorongOverlay({
  stageRef,
  touchpoint,
  state = "idle",
  defaultPosition = "bottom-right",
  chatOpen = false,
  showBubble = false,
  bubbleText,
  bubbleActions = [],
  onTap,
  onBubbleAction,
  onDragEnd,
}: PorongOverlayProps) {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const {
    position,
    isPressed,
    isDragging,
    isSnapping,
    handlePointerDown,
    handlePointerMove,
    handlePointerEnd,
    handleClick,
  } = usePorongDrag({
    stageRef,
    overlayRef,
    defaultPosition,
    chatOpen,
    onTap,
    onDragEnd,
  });

  const visualState = resolveVisualState({
    state,
    isPressed,
    isDragging,
    isSnapping,
  });
  const style =
    position === null
      ? undefined
      : {
          left: `${position.x}px`,
          top: `${position.y}px`,
        };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    onTap?.();
  };

  return (
    <div
      ref={overlayRef}
      className={`porong-overlay ${chatOpen ? "panel-open" : ""} ${
        isDragging ? "is-dragging" : ""
      } ${isSnapping ? "is-snapping" : ""}`}
      data-state={visualState}
      style={style}
    >
      {showBubble && (
        <PorongSpeechBubble
          touchpoint={touchpoint}
          text={bubbleText}
          actions={bubbleActions}
          onAction={onBubbleAction}
        />
      )}

      <button
        type="button"
        className="porong-avatar-button"
        aria-label="뽀롱쌤 AI 학습코치 열기"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerEnd}
        onPointerCancel={handlePointerEnd}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
      >
        <PorongMascot state={visualState} />
      </button>
    </div>
  );
}

function resolveVisualState({
  state,
  isPressed,
  isDragging,
  isSnapping,
}: {
  state: PorongOverlayState;
  isPressed: boolean;
  isDragging: boolean;
  isSnapping: boolean;
}) {
  if (isDragging) {
    return "dragging";
  }

  if (isPressed) {
    return "touched";
  }

  if (isSnapping) {
    return "snapping";
  }

  return state;
}
