"use client";

import dynamic from "next/dynamic";

const SmartAllCoachApp = dynamic(
  () =>
    import("@/components/smartall/SmartAllCoachApp").then(
      (module) => module.SmartAllCoachApp,
    ),
  {
    ssr: false,
    loading: () => (
      <main className="demo-page">
        <section
          className="smartall-tablet theme-lower"
          aria-label="스마트올 AI 학습코치 목업을 불러오는 중"
        />
      </main>
    ),
  },
);

export function SmartAllCoachClient() {
  return <SmartAllCoachApp />;
}
