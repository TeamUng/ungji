"use client";

import type {
  PointerEvent as ReactPointerEvent,
  RefObject,
} from "react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  animate,
  useMotionValue,
  useReducedMotion,
  useSpring,
} from "motion/react";
import type {
  PorongBounds,
  PorongPoint,
  PorongSnapPoint,
} from "@/components/porong/porongTypes";
import {
  clampPorongPosition,
  getPorongSnapPosition,
} from "./usePorongSnap";
import { useDizzyShake } from "./useDizzyShake";

type DragState = {
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
  moved: boolean;
};

type MoveOptions = {
  immediate?: boolean;
};

const DRAG_DISTANCE_THRESHOLD = 8;
const RELEASE_ANIMATION_MS = 240;
const DRAG_ROTATE_FACTOR = 0.08;
const MAX_DRAG_ROTATE = 8;
const MEASUREMENT_RETRY_LIMIT = 10;

export function usePorongDrag({
  stageRef,
  overlayRef,
  defaultPosition,
  initialPosition,
  chatOpen,
  onTap,
  onDragEnd,
  onDizzy,
  onInteractionStart,
  onInteractionMove,
  onInteractionEnd,
}: {
  stageRef: RefObject<HTMLElement | null>;
  overlayRef: RefObject<HTMLDivElement | null>;
  defaultPosition: PorongSnapPoint;
  initialPosition?: PorongPoint | null;
  chatOpen: boolean;
  onTap?: () => void;
  onDragEnd?: (position: PorongPoint) => void;
  onDizzy?: () => void;
  onInteractionStart?: (point: PorongPoint) => void;
  onInteractionMove?: (point: PorongPoint) => void;
  onInteractionEnd?: (point: PorongPoint) => void;
}) {
  const shouldReduceMotion = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotate = useMotionValue(0);
  const springConfig = shouldReduceMotion
    ? { stiffness: 1000, damping: 80, mass: 0.6 }
    : { stiffness: 360, damping: 30, mass: 0.7 };
  const springX = useSpring(x, springConfig);
  const springY = useSpring(y, springConfig);
  const [isReady, setIsReady] = useState(false);
  const [isPressed, setIsPressed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isSnapping, setIsSnapping] = useState(false);
  const dragStateRef = useRef<DragState | null>(null);
  const positionRef = useRef<PorongPoint | null>(null);
  const ignoreNextClickRef = useRef(false);
  const releaseTimerRef = useRef<number | null>(null);
  const handleDizzy = useCallback(() => {
    onDizzy?.();
  }, [onDizzy]);
  const { recordDizzySample, resetDizzySamples } = useDizzyShake({
    enabled: true,
    onDizzy: handleDizzy,
  });

  const moveToPosition = useCallback(
    (point: PorongPoint, options: MoveOptions = {}) => {
      positionRef.current = point;

      if (options.immediate || shouldReduceMotion) {
        x.set(point.x);
        y.set(point.y);
        springX.set(point.x);
        springY.set(point.y);
        return;
      }

      animate(x, point.x, {
        type: "spring",
        stiffness: 380,
        damping: 31,
        mass: 0.72,
      });
      animate(y, point.y, {
        type: "spring",
        stiffness: 380,
        damping: 31,
        mass: 0.72,
      });
    },
    [shouldReduceMotion, springX, springY, x, y],
  );

  useLayoutEffect(() => {
    let retryCount = 0;
    let frame = 0;

    const updateDefaultPosition = () => {
      const measurements = getMeasurements(stageRef, overlayRef);

      if (!measurements) {
        // 첫 렌더 직후에는 부모 stage ref가 아직 준비되지 않을 수 있습니다.
        // 이때 한 번 실패하고 끝내면 오버레이가 계속 숨겨지므로, 아주 짧게만 재측정합니다.
        if (retryCount < MEASUREMENT_RETRY_LIMIT) {
          retryCount += 1;
          frame = window.requestAnimationFrame(updateDefaultPosition);
        }
        return;
      }

      const current = positionRef.current;
      const nextPosition = current
        ? clampPorongPosition({
            point: current,
            stage: measurements.stage,
            overlay: measurements.overlay,
            chatOpen,
          })
        : initialPosition
          ? clampPorongPosition({
              point: initialPosition,
              stage: measurements.stage,
              overlay: measurements.overlay,
              chatOpen,
            })
        : getPorongSnapPosition({
            snapPoint: defaultPosition,
            stage: measurements.stage,
            overlay: measurements.overlay,
            chatOpen,
          });

      moveToPosition(nextPosition, { immediate: !isReady });
      setIsReady(true);
    };

    frame = window.requestAnimationFrame(updateDefaultPosition);

    window.addEventListener("resize", updateDefaultPosition);
    window.addEventListener("orientationchange", updateDefaultPosition);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", updateDefaultPosition);
      window.removeEventListener("orientationchange", updateDefaultPosition);
    };
  }, [
    chatOpen,
    defaultPosition,
    initialPosition,
    isReady,
    moveToPosition,
    overlayRef,
    stageRef,
  ]);

  useEffect(() => {
    return () => {
      if (releaseTimerRef.current !== null) {
        window.clearTimeout(releaseTimerRef.current);
      }
    };
  }, []);

  const getCurrentPosition = useCallback(() => {
    const measurements = getMeasurements(stageRef, overlayRef);

    if (!measurements) {
      return null;
    }

    const renderedPosition = getRenderedPosition({
      stageRef,
      overlayRef,
      measurements,
      chatOpen,
    });

    if (renderedPosition) {
      positionRef.current = renderedPosition;
      return renderedPosition;
    }

    return (
      positionRef.current ??
      getPorongSnapPosition({
        snapPoint: defaultPosition,
        stage: measurements.stage,
        overlay: measurements.overlay,
        chatOpen,
      })
    );
  }, [chatOpen, defaultPosition, overlayRef, stageRef]);

  const handlePointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) {
      return;
    }

    const currentPosition = getCurrentPosition();

    if (!currentPosition) {
      return;
    }

    dragStateRef.current = {
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: currentPosition.x,
      startY: currentPosition.y,
      moved: false,
    };

    resetDizzySamples();
    setIsPressed(true);
    setIsSnapping(false);
    onInteractionStart?.(currentPosition);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const dragState = dragStateRef.current;
    const measurements = getMeasurements(stageRef, overlayRef);

    if (!dragState || !measurements) {
      return;
    }

    const deltaX = event.clientX - dragState.startClientX;
    const deltaY = event.clientY - dragState.startClientY;
    const dragDistance = Math.hypot(deltaX, deltaY);

    if (!dragState.moved && dragDistance >= DRAG_DISTANCE_THRESHOLD) {
      dragState.moved = true;
      setIsDragging(true);
    }

    if (!dragState.moved) {
      return;
    }

    const nextPosition = clampPorongPosition({
      point: {
        x: dragState.startX + deltaX,
        y: dragState.startY + deltaY,
      },
      stage: measurements.stage,
      overlay: measurements.overlay,
      chatOpen,
    });

    positionRef.current = nextPosition;
    x.set(nextPosition.x);
    y.set(nextPosition.y);
    rotate.set(
      clamp(deltaX * DRAG_ROTATE_FACTOR, -MAX_DRAG_ROTATE, MAX_DRAG_ROTATE),
    );
    onInteractionMove?.(nextPosition);
    recordDizzySample({ x: event.clientX, y: event.clientY });
  };

  const handlePointerEnd = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const dragState = dragStateRef.current;

    if (!dragState) {
      return;
    }

    if (event.currentTarget.hasPointerCapture(dragState.pointerId)) {
      event.currentTarget.releasePointerCapture(dragState.pointerId);
    }

    setIsPressed(false);
    setIsDragging(false);
    resetDizzySamples();

    if (!dragState.moved) {
      ignoreNextClickRef.current = true;
      dragStateRef.current = null;
      onTap?.();
      return;
    }

    const measurements = getMeasurements(stageRef, overlayRef);

    if (!measurements) {
      dragStateRef.current = null;
      rotate.set(0);
      return;
    }

    const currentPosition = positionRef.current ?? {
      x: dragState.startX,
      y: dragState.startY,
    };
    const finalPosition = clampPorongPosition({
      point: currentPosition,
      stage: measurements.stage,
      overlay: measurements.overlay,
      chatOpen,
    });

    onInteractionEnd?.(finalPosition);
    moveToPosition(finalPosition);
    rotate.set(0);
    setIsSnapping(true);
    ignoreNextClickRef.current = true;
    onDragEnd?.(finalPosition);

    if (releaseTimerRef.current !== null) {
      window.clearTimeout(releaseTimerRef.current);
    }

    releaseTimerRef.current = window.setTimeout(() => {
      setIsSnapping(false);
    }, shouldReduceMotion ? 80 : RELEASE_ANIMATION_MS);

    dragStateRef.current = null;
  };

  const handleClick = () => {
    if (ignoreNextClickRef.current) {
      ignoreNextClickRef.current = false;
      return;
    }

    onTap?.();
  };

  return {
    x: shouldReduceMotion ? x : springX,
    y: shouldReduceMotion ? y : springY,
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
  };
}

function getMeasurements(
  stageRef: RefObject<HTMLElement | null>,
  overlayRef: RefObject<HTMLDivElement | null>,
) {
  const stage = stageRef.current;
  const overlay = overlayRef.current;

  if (!stage || !overlay) {
    return null;
  }

  const stageRect = stage.getBoundingClientRect();
  const overlayRect = overlay.getBoundingClientRect();
  const visibleStageWidth = Math.min(
    stageRect.width,
    window.innerWidth - Math.max(stageRect.left, 0),
  );
  const visibleStageHeight = Math.min(
    stageRect.height,
    window.innerHeight - Math.max(stageRect.top, 0),
  );

  return {
    stage: {
      // 스마트올 목업이 뷰포트보다 커질 때도 학생 눈에 보이는 영역 안에서만 움직이게 합니다.
      width: visibleStageWidth,
      height: visibleStageHeight,
    } satisfies PorongBounds,
    overlay: {
      width: overlayRect.width,
      height: overlayRect.height,
    } satisfies PorongBounds,
  };
}

function getRenderedPosition({
  stageRef,
  overlayRef,
  measurements,
  chatOpen,
}: {
  stageRef: RefObject<HTMLElement | null>;
  overlayRef: RefObject<HTMLDivElement | null>;
  measurements: ReturnType<typeof getMeasurements>;
  chatOpen: boolean;
}) {
  const stage = stageRef.current;
  const overlay = overlayRef.current;

  if (!stage || !overlay || !measurements) {
    return null;
  }

  const stageRect = stage.getBoundingClientRect();
  const overlayRect = overlay.getBoundingClientRect();

  return clampPorongPosition({
    point: {
      x: overlayRect.left - stageRect.left,
      y: overlayRect.top - stageRect.top,
    },
    stage: measurements.stage,
    overlay: measurements.overlay,
    chatOpen,
  });
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
