"use client";

import type { KeyboardEvent, RefObject } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { TargetAndTransition, Transition } from "motion/react";
import { PorongMascot } from "./PorongMascot";
import { PorongSpeechBubble } from "./PorongSpeechBubble";
import type {
  PorongBubbleAction,
  PorongOverlayState,
  PorongPoint,
  PorongSnapPoint,
  PorongTouchpoint,
} from "./porongTypes";
import { usePorongDrag } from "./usePorongDrag";
import { usePorongInteractionZones } from "./usePorongInteractionZones";

type PorongOverlayProps = {
  stageRef: RefObject<HTMLElement | null>;
  touchpoint?: PorongTouchpoint;
  state?: PorongOverlayState;
  defaultPosition?: PorongSnapPoint;
  initialPosition?: PorongPoint | null;
  chatOpen?: boolean;
  showBubble?: boolean;
  bubbleText?: string;
  bubbleActions?: PorongBubbleAction[];
  enableInteractionZones?: boolean;
  onTap?: () => void;
  onBubbleAction?: (action: PorongBubbleAction) => void;
  onDragEnd?: (position: PorongPoint) => void;
};

const DIZZY_BUBBLE_TEXT = "뽀롱~ 어지러워! 천천히 옮겨줘~";
const DIZZY_VISIBLE_MS = 2000;

export function PorongOverlay({
  stageRef,
  state = "idle",
  defaultPosition = "bottom-right",
  initialPosition,
  chatOpen = false,
  showBubble = false,
  bubbleText,
  bubbleActions = [],
  enableInteractionZones = true,
  onTap,
  onBubbleAction,
  onDragEnd,
}: PorongOverlayProps) {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const dizzyTimerRef = useRef<number | null>(null);
  const [isDizzy, setIsDizzy] = useState(false);
  const {
    activeZone,
    cacheZones,
    updateActiveZone,
    clearActiveZone,
  } = usePorongInteractionZones({
    stageRef,
    overlayRef,
    enabled: enableInteractionZones && !chatOpen,
  });
  const triggerDizzy = useCallback(() => {
    setIsDizzy(true);

    if (dizzyTimerRef.current !== null) {
      window.clearTimeout(dizzyTimerRef.current);
    }

    dizzyTimerRef.current = window.setTimeout(() => {
      setIsDizzy(false);
    }, DIZZY_VISIBLE_MS);
  }, []);
  const handleInteractionStart = useCallback(
    (point: { x: number; y: number }) => {
      cacheZones();
      updateActiveZone(point);
    },
    [cacheZones, updateActiveZone],
  );

  const {
    x,
    y,
    rotate,
    isReady,
    isPressed,
    isDragging,
    isSnapping,
    shouldReduceMotion,
    handlePointerDown,
    handlePointerMove,
    handlePointerEnd,
    handleClick,
  } = usePorongDrag({
    stageRef,
    overlayRef,
    defaultPosition,
    initialPosition,
    chatOpen,
    onTap,
    onDragEnd,
    onDizzy: triggerDizzy,
    onInteractionStart: handleInteractionStart,
    onInteractionMove: updateActiveZone,
    onInteractionEnd: updateActiveZone,
  });
  const hasActiveZoneBubble = !isDizzy && !chatOpen && Boolean(activeZone);

  const visualState = resolveVisualState({
    state,
    isDizzy,
    isPressed,
    isDragging,
    isSnapping,
    hasActiveZone: hasActiveZoneBubble,
  });
  const shouldShowBubble = isDizzy || hasActiveZoneBubble || showBubble;
  const resolvedBubbleText = isDizzy
    ? DIZZY_BUBBLE_TEXT
    : activeZone?.suggestion ?? bubbleText;
  const resolvedBubbleActions =
    isDizzy || hasActiveZoneBubble ? [] : bubbleActions;
  const resolvedBubbleEyebrow = hasActiveZoneBubble
    ? activeZone?.label
    : undefined;
  useEffect(() => {
    return () => {
      if (dizzyTimerRef.current !== null) {
        window.clearTimeout(dizzyTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (chatOpen) {
      clearActiveZone();
    }
  }, [chatOpen, clearActiveZone]);

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    onTap?.();
  };

  if (state === "hidden") {
    return null;
  }

  return (
    <motion.div
      ref={overlayRef}
      className={`porong-overlay ${chatOpen ? "panel-open" : ""} ${
        isDragging ? "is-dragging" : ""
      } ${isSnapping ? "is-snapping" : ""}`}
      data-state={visualState}
      data-ready={isReady ? "true" : "false"}
      style={{ x, y }}
    >
      <AnimatePresence>
        {shouldShowBubble && (
          <motion.div
            key={isDizzy ? "dizzy-bubble" : "touchpoint-bubble"}
            initial={shouldReduceMotion ? false : { opacity: 0, scale: 0.92, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={shouldReduceMotion ? undefined : { opacity: 0, scale: 0.96, y: 6 }}
            transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
          >
            <PorongSpeechBubble
              eyebrow={resolvedBubbleEyebrow}
              text={resolvedBubbleText}
              actions={resolvedBubbleActions}
              onAction={onBubbleAction}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        type="button"
        className="porong-avatar-button"
        aria-label="뽀롱쌤 AI 학습코치 열기"
        animate={getAvatarAnimation(visualState, shouldReduceMotion)}
        transition={getAvatarTransition(visualState, shouldReduceMotion)}
        style={visualState === "dragging" ? { rotate } : undefined}
        whileTap={shouldReduceMotion ? undefined : { scale: 1.08 }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerEnd}
        onPointerCancel={handlePointerEnd}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
      >
        <PorongMascot state={visualState} />
      </motion.button>
    </motion.div>
  );
}

function resolveVisualState({
  state,
  isDizzy,
  isPressed,
  isDragging,
  isSnapping,
  hasActiveZone,
}: {
  state: PorongOverlayState;
  isDizzy: boolean;
  isPressed: boolean;
  isDragging: boolean;
  isSnapping: boolean;
  hasActiveZone: boolean;
}) {
  if (isDizzy) {
    return "dizzy";
  }

  if (isDragging) {
    return "dragging";
  }

  if (isPressed) {
    return "touched";
  }

  if (isSnapping) {
    return "snapping";
  }

  if (hasActiveZone) {
    return "hint";
  }

  return state;
}

function getAvatarAnimation(
  state: PorongOverlayState,
  shouldReduceMotion: boolean | null,
): TargetAndTransition {
  if (shouldReduceMotion) {
    return { scale: 1, y: 0, rotate: 0 };
  }

  if (state === "dizzy") {
    return {
      rotate: [-10, 10, -6, 6, 0],
      scale: [1.04, 1.06, 1.02, 1],
      y: [0, -3, 2, 0],
    };
  }

  if (state === "snapping") {
    return {
      scale: [1.05, 0.96, 1],
      y: [-4, 4, 0],
    };
  }

  if (state === "dragging") {
    return {
      scale: 1.04,
      y: 5,
    };
  }

  if (state === "touched") {
    return {
      scale: [1, 1.08, 1],
      y: [0, -3, 0],
    };
  }

  if (state === "cheer") {
    return {
      scale: [1, 1.08, 0.98, 1],
      y: [0, -16, 4, 0],
      rotate: [0, -4, 3, 0],
    };
  }

  if (state === "comfort") {
    return {
      scale: [1, 1.03, 1],
      y: [0, -3, 0],
    };
  }

  if (state === "thinking" || state === "hint") {
    return {
      y: [0, -5, 0],
      rotate: [0, 1.5, 0],
    };
  }

  if (state === "speaking") {
    return {
      y: [0, -3, 0],
      scale: [1, 1.025, 1],
    };
  }

  if (state === "confused") {
    return {
      rotate: [-2, 3, -2],
    };
  }

  if (state === "idle" || state === "welcome") {
    return {
      y: [0, -4, 0],
      scale: 1,
    };
  }

  return { scale: 1, y: 0, rotate: 0 };
}

function getAvatarTransition(
  state: PorongOverlayState,
  shouldReduceMotion: boolean | null,
): Transition {
  if (shouldReduceMotion) {
    return { duration: 0 };
  }

  if (state === "idle" || state === "welcome") {
    return {
      duration: 2.5,
      repeat: Infinity,
      ease: "easeInOut",
    };
  }

  if (state === "dizzy") {
    return {
      duration: 0.95,
      ease: "easeInOut",
    };
  }

  if (state === "thinking" || state === "hint") {
    return {
      duration: 1.5,
      repeat: Infinity,
      ease: "easeInOut",
    };
  }

  if (state === "speaking") {
    return {
      duration: 1.1,
      repeat: Infinity,
      ease: "easeInOut",
    };
  }

  if (state === "comfort") {
    return {
      duration: 2.6,
      repeat: Infinity,
      ease: "easeInOut",
    };
  }

  if (state === "confused") {
    return {
      duration: 1.7,
      repeat: Infinity,
      ease: "easeInOut",
    };
  }

  if (state === "dragging") {
    return {
      type: "spring",
      stiffness: 360,
      damping: 28,
      mass: 0.65,
    };
  }

  if (state === "snapping") {
    return {
      duration: 0.34,
      ease: "easeOut",
    };
  }

  return {
    duration: 0.22,
    ease: "easeOut",
  };
}
