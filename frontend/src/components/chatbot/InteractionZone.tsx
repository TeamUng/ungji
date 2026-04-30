"use client";

import {
  useEffect,
  useRef,
  type AriaRole,
  type CSSProperties,
  type ReactNode,
} from "react";
import { chatbotSuggestions, type InteractionZoneId, type InteractionZoneType } from "./chatbotSuggestions";
import { useInteractionZones } from "./useInteractionZones";

type InteractionZoneProps = {
  id: InteractionZoneId;
  label: string;
  type: InteractionZoneType;
  suggestion?: string;
  className?: string;
  ariaLabel?: string;
  role?: AriaRole;
  style?: CSSProperties;
  children: ReactNode;
};

export function InteractionZone({
  id,
  label,
  type,
  suggestion = chatbotSuggestions[id],
  className,
  ariaLabel,
  role,
  style,
  children,
}: InteractionZoneProps) {
  const zoneRef = useRef<HTMLDivElement | null>(null);
  const { activeZoneId, registerZone, unregisterZone } = useInteractionZones();

  useEffect(() => {
    const element = zoneRef.current;

    if (!element) {
      return;
    }

    registerZone({
      id,
      label,
      type,
      suggestion,
      element,
    });

    return () => {
      unregisterZone(id);
    };
  }, [id, label, registerZone, suggestion, type, unregisterZone]);

  return (
    <div
      ref={zoneRef}
      className={["interaction-zone", className].filter(Boolean).join(" ")}
      data-active={activeZoneId === id ? "true" : "false"}
      data-zone-id={id}
      role={role}
      aria-label={ariaLabel}
      style={style}
    >
      {children}
    </div>
  );
}
