import type { SmartAllView } from "@/data/smartallMockData";
import styles from "./SmartAllHome.module.css";

type TopNavProps = {
  activeView: SmartAllView;
  onViewChange: (view: SmartAllView) => void;
};

const navItems: Array<{ label: string; view?: SmartAllView }> = [
  { label: "오늘의 학습", view: "today" },
  { label: "AI맞춤", view: "ai-match" },
  { label: "단원평가센터" },
  { label: "쉬는시간" },
];

export function TopNav({ activeView, onViewChange }: TopNavProps) {
  return (
    <header className={styles.topNav}>
      <div className={styles.logoArea} aria-label="웅진 스마트올">
        <button type="button" className={styles.backCircle} aria-label="이전">
          ˅
        </button>
        <span className={styles.logoText}>
          <small>웅진씽크빅</small>
          <strong>
            smart<span>All</span>
          </strong>
        </span>
      </div>

      <nav className={styles.mainNav} aria-label="스마트올 메뉴">
        {navItems.map((item) => {
          const isActive = item.view === activeView;

          return (
            <button
              key={item.label}
              type="button"
              className={isActive ? styles.activeNavItem : ""}
              onClick={() => {
                if (item.view) {
                  onViewChange(item.view);
                }
              }}
            >
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className={styles.topTools} aria-label="상단 도구">
        <button type="button" className={styles.allButton}>
          전체
        </button>
        <button type="button" aria-label="검색">
          <span className={`${styles.topIcon} ${styles.searchIcon}`} />
        </button>
        <button type="button" aria-label="즐겨찾기">
          <span className={`${styles.topIcon} ${styles.starIcon}`} />
        </button>
        <button type="button" aria-label="메시지">
          <span className={`${styles.topIcon} ${styles.messageIcon}`} />
        </button>
        <button type="button" aria-label="메뉴">
          <span className={`${styles.topIcon} ${styles.menuIcon}`} />
        </button>
      </div>
    </header>
  );
}
