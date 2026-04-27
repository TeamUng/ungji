import { useState } from "react";
import type { Touchpoint } from "@/types/chat";

export type CoachSurface = "hidden" | "floating" | "drawer";

export const defaultSurfaceByTouchpoint: Record<Touchpoint, CoachSurface> = {
  tp1: "floating",
  tp2: "floating",
  tp3: "floating",
  tp4: "drawer",
  tp5: "floating",
};

export function useCoachLayer() {
  const [surface, setSurface] = useState<CoachSurface>("floating");
  const [touchpoint, setTouchpoint] = useState<Touchpoint>("tp1");

  function showFloating(nextTouchpoint: Touchpoint) {
    setTouchpoint(nextTouchpoint);
    setSurface("floating");
  }

  function openDrawer(nextTouchpoint: Touchpoint = "tp4") {
    setTouchpoint(nextTouchpoint);
    setSurface("drawer");
  }

  function hide() {
    setSurface("hidden");
  }

  return {
    surface,
    touchpoint,
    showFloating,
    openDrawer,
    hide,
  };
}
