"use client";

import dynamic from "next/dynamic";
import type { SmartAllHomeProps } from "./SmartAllHome";
import styles from "./SmartAllHome.module.css";

const SmartAllHome = dynamic(
  () => import("./SmartAllHome").then((module) => module.SmartAllHome),
  {
    ssr: false,
    loading: () => (
      <main className={styles.smartallPage}>
        <section
          className={styles.smartallStage}
          aria-label="스마트올 홈 화면을 불러오는 중"
        />
      </main>
    ),
  },
);

export function SmartAllHomeClient(props: SmartAllHomeProps) {
  return <SmartAllHome {...props} />;
}
