import type { PorongOverlayState } from "./porongTypes";

const mascotBasePath = "/assets/porong/mascot";

export const porongMascotAssets: Record<PorongOverlayState, string> = {
  idle: `${mascotBasePath}/porong-overlay-idle.webp`,
  welcome: `${mascotBasePath}/porong-overlay-welcome.webp`,
  thinking: `${mascotBasePath}/porong-overlay-thinking.webp`,
  speaking: `${mascotBasePath}/porong-overlay-speaking.webp`,
  hint: `${mascotBasePath}/porong-overlay-hint.webp`,
  cheer: `${mascotBasePath}/porong-overlay-cheer.webp`,
  comfort: `${mascotBasePath}/porong-overlay-comfort.webp`,
  confused: `${mascotBasePath}/porong-overlay-confused.webp`,
  dizzy: `${mascotBasePath}/porong-overlay-confused.webp`,
  touched: `${mascotBasePath}/porong-overlay-touched.webp`,
  dragging: `${mascotBasePath}/porong-overlay-dragging.webp`,
  hanging: `${mascotBasePath}/porong-overlay-hanging.webp`,
  snapping: `${mascotBasePath}/porong-overlay-snapping.webp`,
  edge: `${mascotBasePath}/porong-overlay-edge.webp`,
  hidden: `${mascotBasePath}/porong-overlay-idle.webp`,
};

export const porongUiAssets = {
  sparkle: "/assets/porong/ui/sparkle.svg",
  star: "/assets/porong/ui/star.svg",
  speechTail: "/assets/porong/ui/speech-tail.svg",
  wand: "/assets/porong/ui/wand.svg",
};
