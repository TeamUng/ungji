"use client";

import { useCallback, useEffect, useRef, type RefObject } from "react";
import type { InteractionZoneId } from "@/components/chatbot/chatbotSuggestions";
import {
  useOptionalInteractionZoneContext,
  type MeasuredInteractionZone,
} from "@/components/chatbot/InteractionZoneProvider";
import { isPointInsideRect } from "@/lib/geometry";
import type { PorongPoint } from "./porongTypes";

type UsePorongInteractionZonesArgs = {
  stageRef: RefObject<HTMLElement | null>;
  overlayRef: RefObject<HTMLDivElement | null>;
  enabled?: boolean;
};

export function usePorongInteractionZones({
  stageRef,
  overlayRef,
  enabled = true,
}: UsePorongInteractionZonesArgs) {
  const context = useOptionalInteractionZoneContext();
  const cachedZonesRef = useRef<MeasuredInteractionZone[]>([]);
  const activeZoneIdRef = useRef<InteractionZoneId | null>(null);

  const activeZone = context?.activeZoneId
    ? context.getZone(context.activeZoneId)
    : undefined;

  useEffect(() => {
    activeZoneIdRef.current = context?.activeZoneId ?? null;
  }, [context?.activeZoneId]);

  const cacheZones = useCallback(() => {
    if (!enabled || !context) {
      cachedZonesRef.current = [];
      return;
    }

    cachedZonesRef.current = context.measureZones();
  }, [context, enabled]);

  const updateActiveZone = useCallback(
    (point: PorongPoint) => {
      if (!enabled || !context) {
        return;
      }

      const stage = stageRef.current;
      const overlay = overlayRef.current;

      if (!stage || !overlay) {
        return;
      }

      if (cachedZonesRef.current.length === 0) {
        cachedZonesRef.current = context.measureZones();
      }

      const stageRect = stage.getBoundingClientRect();
      const overlayRect = overlay.getBoundingClientRect();
      const mascotCenter = {
        x: stageRect.left + point.x + overlayRect.width / 2,
        y: stageRect.top + point.y + overlayRect.height / 2,
      };
      const matchedZones = cachedZonesRef.current.filter((zone) =>
        isPointInsideRect(mascotCenter, zone.rect),
      );
      const nextZone = matchedZones.reduce<MeasuredInteractionZone | undefined>(
        (smallest, zone) => {
          if (!smallest) {
            return zone;
          }

          const smallestArea = smallest.rect.width * smallest.rect.height;
          const zoneArea = zone.rect.width * zone.rect.height;

          return zoneArea < smallestArea ? zone : smallest;
        },
        undefined,
      );
      const nextZoneId = nextZone?.id ?? null;

      if (activeZoneIdRef.current !== nextZoneId) {
        activeZoneIdRef.current = nextZoneId;
        context.setActiveZoneId(nextZoneId);
      }
    },
    [context, enabled, overlayRef, stageRef],
  );

  const clearActiveZone = useCallback(() => {
    if (!context) {
      return;
    }

    activeZoneIdRef.current = null;
    cachedZonesRef.current = [];
    context.setActiveZoneId(null);
  }, [context]);

  return {
    activeZone,
    cacheZones,
    updateActiveZone,
    clearActiveZone,
    hasZoneProvider: Boolean(context),
  };
}
