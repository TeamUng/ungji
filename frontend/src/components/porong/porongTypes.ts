export type PorongOverlayState =
  | "idle"
  | "welcome"
  | "thinking"
  | "speaking"
  | "hint"
  | "cheer"
  | "comfort"
  | "confused"
  | "dizzy"
  | "touched"
  | "dragging"
  | "hanging"
  | "snapping"
  | "edge"
  | "hidden";

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
  action?: "navigate" | "open_chat";
  targetStep?: "home" | "learning" | "help" | "complete" | "exit" | "wrapup";
  targetTaskIndex?: number;
};

export type PorongPoint = {
  x: number;
  y: number;
};

export type PorongBounds = {
  width: number;
  height: number;
};
