import type {
  PorongPoint,
  PorongSnapPoint,
} from "@/components/porong/porongTypes";

type Bounds = {
  width: number;
  height: number;
};

const EDGE_PADDING = 18;
const TOP_SAFE_PADDING = 58;
const CHAT_PANEL_WIDTH = 390;
const MOBILE_CHAT_PANEL_RATIO = 0.58;

const DEFAULT_SNAP_POINTS: PorongSnapPoint[] = [
  "bottom-right",
  "middle-right",
  "bottom-left",
];

export function getPorongSnapPosition({
  snapPoint,
  stage,
  overlay,
  chatOpen,
}: {
  snapPoint: PorongSnapPoint;
  stage: Bounds;
  overlay: Bounds;
  chatOpen: boolean;
}): PorongPoint {
  const safe = getSafeBounds({ stage, overlay, chatOpen });
  const left = safe.minX;
  const right = safe.maxX;
  const top = safe.minY;
  const middleY = safe.minY + (safe.maxY - safe.minY) / 2;
  const bottom = safe.maxY;

  switch (snapPoint) {
    case "top-left":
      return { x: left, y: top };
    case "top-right":
      return { x: right, y: top };
    case "middle-left":
      return { x: left, y: middleY };
    case "middle-right":
      return { x: right, y: middleY };
    case "bottom-left":
      return { x: left, y: bottom };
    case "bottom-right":
    default:
      return { x: right, y: bottom };
  }
}

export function getNearestPorongSnap({
  point,
  stage,
  overlay,
  chatOpen,
  snapPoints = DEFAULT_SNAP_POINTS,
}: {
  point: PorongPoint;
  stage: Bounds;
  overlay: Bounds;
  chatOpen: boolean;
  snapPoints?: PorongSnapPoint[];
}) {
  const candidates = snapPoints.map((snapPoint) => ({
    snapPoint,
    position: getPorongSnapPosition({ snapPoint, stage, overlay, chatOpen }),
  }));

  return candidates.reduce((nearest, candidate) => {
    const nearestDistance = getSquaredDistance(point, nearest.position);
    const candidateDistance = getSquaredDistance(point, candidate.position);

    return candidateDistance < nearestDistance ? candidate : nearest;
  });
}

export function clampPorongPosition({
  point,
  stage,
  overlay,
  chatOpen,
}: {
  point: PorongPoint;
  stage: Bounds;
  overlay: Bounds;
  chatOpen: boolean;
}) {
  const safe = getSafeBounds({ stage, overlay, chatOpen });

  return {
    x: clamp(point.x, safe.minX, safe.maxX),
    y: clamp(point.y, safe.minY, safe.maxY),
  };
}

function getSafeBounds({
  stage,
  overlay,
  chatOpen,
}: {
  stage: Bounds;
  overlay: Bounds;
  chatOpen: boolean;
}) {
  const mobilePanelOpen = chatOpen && stage.width <= 980;
  const desktopPanelOpen = chatOpen && stage.width > 980;
  const rightReserved = desktopPanelOpen ? CHAT_PANEL_WIDTH : 0;
  const bottomReserved = mobilePanelOpen ? stage.height * MOBILE_CHAT_PANEL_RATIO : 0;

  return {
    minX: EDGE_PADDING,
    minY: TOP_SAFE_PADDING,
    maxX: Math.max(
      EDGE_PADDING,
      stage.width - overlay.width - EDGE_PADDING - rightReserved,
    ),
    maxY: Math.max(
      TOP_SAFE_PADDING,
      stage.height - overlay.height - EDGE_PADDING - bottomReserved,
    ),
  };
}

function getSquaredDistance(a: PorongPoint, b: PorongPoint) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;

  return dx * dx + dy * dy;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

