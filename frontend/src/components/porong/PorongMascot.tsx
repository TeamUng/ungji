import Image from "next/image";
import type { PorongOverlayState } from "./porongTypes";
import { porongMascotAssets } from "./porongAssets";

type PorongMascotProps = {
  state: PorongOverlayState;
  size?: "sm" | "md" | "lg";
};

export function PorongMascot({ state, size = "md" }: PorongMascotProps) {
  return (
    <span className={`porong-mascot porong-mascot-${size}`} data-state={state}>
      <Image
        src={porongMascotAssets[state]}
        alt=""
        width={768}
        height={667}
        priority
        draggable={false}
      />
      <span className="porong-mascot-glow" aria-hidden="true" />
      <span className="porong-mascot-sparkle" aria-hidden="true" />
      <span className="porong-mascot-star" aria-hidden="true" />
    </span>
  );
}

