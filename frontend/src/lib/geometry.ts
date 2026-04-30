type Point = {
  x: number;
  y: number;
};

type RectLike = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};

export function isPointInsideRect(point: Point, rect: RectLike) {
  return (
    point.x >= rect.left &&
    point.x <= rect.right &&
    point.y >= rect.top &&
    point.y <= rect.bottom
  );
}
