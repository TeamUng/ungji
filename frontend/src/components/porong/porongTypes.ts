export type PorongOverlayState =
  | "idle"
  | "welcome"
  | "thinking"
  | "speaking"
  | "hint"
  | "cheer"
  | "comfort"
  | "confused"
  | "touched"
  | "dragging"
  | "hanging"
  | "snapping"
  | "edge";

export type PorongTouchpoint = "tp1" | "tp2" | "tp3" | "tp4" | "tp5";

export type PorongSnapPoint =
  | "bottom-right"
  | "middle-right"
  | "top-right"
  | "bottom-left"
  | "middle-left"
  | "top-left";

export type PorongBubbleAction = {
  id: string;
  label: string;
};

export type PorongPoint = {
  x: number;
  y: number;
};

