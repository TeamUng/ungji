import type { PropsWithChildren } from "react";
import { SmartAllTopBar } from "@/components/shell/SmartAllTopBar";
import type { CaseId } from "@/types/learning";

type TabletFrameProps = PropsWithChildren<{
  activeCaseId: CaseId;
  onCaseChange: (caseId: CaseId) => void;
}>;

export function TabletFrame({
  activeCaseId,
  onCaseChange,
  children,
}: TabletFrameProps) {
  return (
    <div className="tablet-shell">
      <SmartAllTopBar activeCaseId={activeCaseId} onCaseChange={onCaseChange} />
      {children}
    </div>
  );
}
