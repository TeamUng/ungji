import { SmartAllHomeClient } from "@/components/smartall/SmartAllHomeClient";

export default function Home() {
  return (
    <SmartAllHomeClient
      initialView="today"
      initialMode="rebuilt"
      initialReference={false}
    />
  );
}
