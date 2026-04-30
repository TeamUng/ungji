"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type {
  InteractionZoneId,
  InteractionZoneType,
} from "./chatbotSuggestions";

export type RegisteredInteractionZone = {
  id: InteractionZoneId;
  label: string;
  type: InteractionZoneType;
  suggestion: string;
  element: HTMLElement;
};

export type MeasuredInteractionZone = Omit<
  RegisteredInteractionZone,
  "element"
> & {
  rect: DOMRect;
};

type InteractionZoneContextValue = {
  activeZoneId: InteractionZoneId | null;
  setActiveZoneId: (id: InteractionZoneId | null) => void;
  registerZone: (zone: RegisteredInteractionZone) => void;
  unregisterZone: (id: InteractionZoneId) => void;
  measureZones: () => MeasuredInteractionZone[];
  getZone: (id: InteractionZoneId) => RegisteredInteractionZone | undefined;
};

const InteractionZoneContext =
  createContext<InteractionZoneContextValue | null>(null);

export function InteractionZoneProvider({ children }: { children: ReactNode }) {
  // DOM 요소는 화면 이동 중에도 자주 바뀌지 않으므로 ref에 보관합니다.
  // 이렇게 하면 드래그 중 매 프레임 React state를 바꾸지 않아도 됩니다.
  const zonesRef = useRef(new Map<InteractionZoneId, RegisteredInteractionZone>());
  const [activeZoneId, setActiveZoneId] =
    useState<InteractionZoneId | null>(null);

  const registerZone = useCallback((zone: RegisteredInteractionZone) => {
    zonesRef.current.set(zone.id, zone);
  }, []);

  const unregisterZone = useCallback((id: InteractionZoneId) => {
    zonesRef.current.delete(id);
  }, []);

  const measureZones = useCallback(() => {
    return Array.from(zonesRef.current.values()).map((zone) => ({
      id: zone.id,
      label: zone.label,
      type: zone.type,
      suggestion: zone.suggestion,
      rect: zone.element.getBoundingClientRect(),
    }));
  }, []);

  const getZone = useCallback((id: InteractionZoneId) => {
    return zonesRef.current.get(id);
  }, []);

  const value = useMemo(
    () => ({
      activeZoneId,
      setActiveZoneId,
      registerZone,
      unregisterZone,
      measureZones,
      getZone,
    }),
    [
      activeZoneId,
      getZone,
      measureZones,
      registerZone,
      unregisterZone,
    ],
  );

  return (
    <InteractionZoneContext.Provider value={value}>
      {children}
    </InteractionZoneContext.Provider>
  );
}

export function useInteractionZoneContext() {
  const context = useContext(InteractionZoneContext);

  if (!context) {
    throw new Error(
      "InteractionZoneProvider 안에서만 InteractionZone 훅을 사용할 수 있습니다.",
    );
  }

  return context;
}

export function useOptionalInteractionZoneContext() {
  return useContext(InteractionZoneContext);
}
