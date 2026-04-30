import { SmartAllCoachApp } from "@/components/smartall/SmartAllCoachApp";
import type { DemoCaseId, DemoRunMode } from "@/types/chat";

type TouchpointDemoPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function TouchpointDemoPage({
  searchParams,
}: TouchpointDemoPageProps) {
  const params = (await searchParams) ?? {};
  const caseParam = Array.isArray(params.case) ? params.case[0] : params.case;
  const controlsParam = Array.isArray(params.controls)
    ? params.controls[0]
    : params.controls;
  const modeParam = Array.isArray(params.mode) ? params.mode[0] : params.mode;
  const initialCaseId: DemoCaseId =
    caseParam === "upper-math" ? "upper-math" : "lower-korean";
  const demoMode: DemoRunMode = modeParam === "script" ? "script" : "hybrid";

  return (
    <SmartAllCoachApp
      initialCaseId={initialCaseId}
      demoMode={demoMode}
      showDemoControls={controlsParam === "1"}
    />
  );
}
