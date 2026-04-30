import Image from "next/image";
import styles from "./SmartAllHome.module.css";

type ReferenceBackgroundProps = {
  image: string;
  opacity: number;
  isOverlay?: boolean;
};

export function ReferenceBackground({
  image,
  opacity,
  isOverlay = false,
}: ReferenceBackgroundProps) {
  return (
    <div
      className={`${styles.referenceBackground} ${
        isOverlay ? styles.referenceOverlay : ""
      }`}
      style={{ opacity }}
      aria-hidden="true"
    >
      <Image src={image} alt="" fill sizes="1280px" priority />
    </div>
  );
}
