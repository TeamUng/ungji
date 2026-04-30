import type { QuickActionItem } from "@/data/smartallMockData";
import styles from "./SmartAllHome.module.css";

type QuickActionButtonsProps = {
  actions: QuickActionItem[];
};

export function QuickActionButtons({ actions }: QuickActionButtonsProps) {
  return (
    <div className={styles.quickActions} aria-label="빠른 메뉴">
      {actions.map((action) => (
        <button key={action.label} type="button">
          <span className={`${styles.quickIcon} ${styles[action.icon]}`} />
          {action.label}
        </button>
      ))}
    </div>
  );
}
