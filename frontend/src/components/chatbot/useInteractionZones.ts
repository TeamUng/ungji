"use client";

import { useInteractionZoneContext } from "./InteractionZoneProvider";

export function useInteractionZones() {
  return useInteractionZoneContext();
}
