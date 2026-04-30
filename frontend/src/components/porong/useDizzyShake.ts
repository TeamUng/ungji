"use client";

import { useCallback, useRef } from "react";
import type { PorongPoint } from "./porongTypes";

type PointerSample = PorongPoint & {
  time: number;
};

type UseDizzyShakeArgs = {
  enabled: boolean;
  onDizzy: () => void;
};

const DIZZY_WINDOW_MS = 600;
const DIZZY_DIRECTION_CHANGES = 3;
const DIZZY_HORIZONTAL_DISTANCE = 120;
const DIZZY_MAX_VERTICAL_DISTANCE = 60;
const DIZZY_COOLDOWN_MS = 2000;
const MIN_DIRECTION_DELTA = 4;

export function useDizzyShake({ enabled, onDizzy }: UseDizzyShakeArgs) {
  const samplesRef = useRef<PointerSample[]>([]);
  const lastDizzyAtRef = useRef(-DIZZY_COOLDOWN_MS);

  const resetDizzySamples = useCallback(() => {
    samplesRef.current = [];
  }, []);

  const recordDizzySample = useCallback(
    (point: PorongPoint) => {
      if (!enabled) {
        return false;
      }

      const now = performance.now();
      const samples = [
        ...samplesRef.current.filter(
          (sample) => now - sample.time <= DIZZY_WINDOW_MS,
        ),
        { ...point, time: now },
      ];

      samplesRef.current = samples;

      if (now - lastDizzyAtRef.current < DIZZY_COOLDOWN_MS) {
        return false;
      }

      if (!isDizzyShake(samples)) {
        return false;
      }

      lastDizzyAtRef.current = now;
      samplesRef.current = [];
      onDizzy();
      return true;
    },
    [enabled, onDizzy],
  );

  return {
    recordDizzySample,
    resetDizzySamples,
  };
}

function isDizzyShake(samples: PointerSample[]) {
  if (samples.length < 4) {
    return false;
  }

  let horizontalDistance = 0;
  let lastDirection = 0;
  let directionChanges = 0;
  let minY = samples[0].y;
  let maxY = samples[0].y;

  for (let index = 1; index < samples.length; index += 1) {
    const previous = samples[index - 1];
    const current = samples[index];
    const deltaX = current.x - previous.x;

    horizontalDistance += Math.abs(deltaX);
    minY = Math.min(minY, current.y);
    maxY = Math.max(maxY, current.y);

    if (Math.abs(deltaX) < MIN_DIRECTION_DELTA) {
      continue;
    }

    const direction = Math.sign(deltaX);

    if (lastDirection !== 0 && direction !== lastDirection) {
      directionChanges += 1;
    }

    lastDirection = direction;
  }

  return (
    directionChanges >= DIZZY_DIRECTION_CHANGES &&
    horizontalDistance >= DIZZY_HORIZONTAL_DISTANCE &&
    maxY - minY <= DIZZY_MAX_VERTICAL_DISTANCE
  );
}
