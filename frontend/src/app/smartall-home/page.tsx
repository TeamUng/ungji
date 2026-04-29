import { SmartAllHomeClient } from "@/components/smartall/SmartAllHomeClient";
import type { SmartAllMode, SmartAllView } from "@/data/smartallMockData";

type SmartAllHomePageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function SmartAllHomePage({
  searchParams,
}: SmartAllHomePageProps) {
  const params = await searchParams;
  const initialView = normalizeView(readFirstParam(params.view));
  const initialMode = normalizeMode(readFirstParam(params.mode));
  const initialReference = readFirstParam(params.reference) === "true";

  return (
    <SmartAllHomeClient
      initialView={initialView}
      initialMode={initialMode}
      initialReference={initialReference}
    />
  );
}

function readFirstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function normalizeView(value: string | undefined): SmartAllView {
  return value === "ai-match" ? "ai-match" : "today";
}

function normalizeMode(value: string | undefined): SmartAllMode {
  return value === "reference" ? "reference" : "rebuilt";
}
