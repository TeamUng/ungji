"use client";

import type {
  PointerEvent as ReactPointerEvent,
  RefObject,
} from "react";
import { useEffect, useRef, useState } from "react";
import type {
  PorongPoint,
  PorongSnapPoint,
} from "@/components/porong/porongTypes";
import {
  clampPorongPosition,
  getNearestPorongSnap,
  getPorongSnapPosition,
} from "./usePorongSnap";

type DragState = {
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
  moved: boolean;
};

const DRAG_DISTANCE_THRESHOLD = 8;
const SNAP_ANIMATION_MS = 360;

export function usePorongDrag({
  stageRef,
  overlayRef,
  defaultPosition,
  chatOpen,
  onTap,
  onDragEnd,
}: {
  stageRef: RefObject<HTMLElement | null>;
  overlayRef: RefObject<HTMLDivElement | null>;
  defaultPosition: PorongSnapPoint;
  chatOpen: boolean;
  onTap?: () => void;
  onDragEnd?: (snapPoint: PorongSnapPoint) => void;
}) {
  const [position, setPosition] = useState<PorongPoint | null>(null);
  const [isPressed, setIsPressed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isSnapping, setIsSnapping] = useState(false);
  const dragStateRef = useRef<DragState | null>(null);
  const ignoreNextClickRef = useRef(false);
  const snapTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const updateDefaultPosition = () => {
      const measurements = getMeasurements(stageRef, overlayRef);

      if (!measurements) {
        return;
      }

      setPosition((current) => {
        if (current) {
          return clampPorongPosition({
            point: current,
            stage: measurements.stage,
            overlay: measurements.overlay,
            chatOpen,
          });
        }

        return getPorongSnapPosition({
          snapPoint: defaultPosition,
          stage: measurements.stage,
          overlay: measurements.overlay,
          chatOpen,
        });
      });
    };

    updateDefaultPosition();
    window.addEventListener("resize", updateDefaultPosition);

    return () => {
      window.removeEventListener("resize", updateDefaultPosition);
    };
  }, [chatOpen, defaultPosition, overlayRef, stageRef]);

  useEffect(() => {
    return () => {
      if (snapTimerRef.current !== null) {
        window.clearTimeout(snapTimerRef.current);
      }
    };
  }, []);

  const handlePointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0) {
      return;
    }

    const measurements = getMeasurements(stageRef, overlayRef);

    if (!measurements) {
      return;
    }

    const currentPosition =
      position ??
      getPorongSnapPosition({
        snapPoint: defaultPosition,
        stage: measurements.stage,
        overlay: measurements.overlay,
        chatOpen,
      });

    dragStateRef.current = {
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: currentPosition.x,
      startY: currentPosition.y,
      moved: false,
    };

    // 탭과 드래그를 같은 버튼에서 처리하므로, 눌린 순간만 먼저 표시합니다.
    setIsPressed(true);
    setIsSnapping(false);
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
    const dragDistance = Math.abs(deltaX) + Math.abs(deltaY);

    if (dragDistance >= DRAG_DISTANCE_THRESHOLD) {
      dragState.moved = true;
      setIsDragging(true);
    }

    if (!dragState.moved) {
      return;
    }

    setPosition(
      clampPorongPosition({
        point: {
          x: dragState.startX + deltaX,
          y: dragState.startY + deltaY,
        },
        stage: measurements.stage,
        overlay: measurements.overlay,
        chatOpen,
      }),
    );
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

    if (!dragState.moved) {
      ignoreNextClickRef.current = true;
      dragStateRef.current = null;
      onTap?.();
      return;
    }

    const measurements = getMeasurements(stageRef, overlayRef);

    if (!measurements) {
      dragStateRef.current = null;
      return;
    }

    const currentPosition = position ?? {
      x: dragState.startX,
      y: dragState.startY,
    };
    const nearest = getNearestPorongSnap({
      point: currentPosition,
      stage: measurements.stage,
      overlay: measurements.overlay,
      chatOpen,
    });

    setPosition(nearest.position);
    setIsSnapping(true);
    ignoreNextClickRef.current = true;
    onDragEnd?.(nearest.snapPoint);

    if (snapTimerRef.current !== null) {
      window.clearTimeout(snapTimerRef.current);
    }

    snapTimerRef.current = window.setTimeout(() => {
      setIsSnapping(false);
    }, SNAP_ANIMATION_MS);

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
    position,
    isPressed,
    isDragging,
    isSnapping,
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
      // 기존 스마트올 화면은 일부 뷰포트에서 내부 콘텐츠가 가로로 넓습니다.
      // 오버레이는 학습 화면 전체 폭보다 "학생 눈에 실제 보이는 영역" 안에 있어야 합니다.
      width: visibleStageWidth,
      height: visibleStageHeight,
    },
    overlay: {
      width: overlayRect.width,
      height: overlayRect.height,
    },
  };
}
