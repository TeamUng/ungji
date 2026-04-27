import type { PropsWithChildren } from "react";
import { SmartAllTopBar } from "@/components/shell/SmartAllTopBar";

export function TabletFrame({ children }: PropsWithChildren) {
  return (
    <div className="tablet-shell">
      <SmartAllTopBar />
      {children}
    </div>
  );
}
