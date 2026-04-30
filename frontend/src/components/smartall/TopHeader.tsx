import { IconMock } from "./IconMock";
import styles from "./SmartAllHome.module.css";

const menuItems = ["오늘의 학습", "AI맞춤", "단원평가센터", "쉬는시간"];

export function TopHeader() {
  return (
    <header className={styles.topHeader}>
      <div className={styles.logoArea} aria-label="웅진 스마트올">
        <button type="button" className={styles.backButton} aria-label="뒤로가기">
          <IconMock kind="back" />
        </button>
        <div className={styles.logoText}>
          <small>웅진씽크빅</small>
          <strong>
            smart<span>All</span>
          </strong>
        </div>
      </div>

      <nav className={styles.mainMenu} aria-label="스마트올 메뉴">
        {menuItems.map((item) => (
          <button
            key={item}
            type="button"
            className={item === "오늘의 학습" ? styles.activeMenuItem : ""}
          >
            {item}
          </button>
        ))}
      </nav>

      <div className={styles.headerTools} aria-label="상단 도구">
        <button type="button" className={styles.allPill}>
          전체
        </button>
        <button type="button" aria-label="검색">
          <IconMock kind="search" />
        </button>
        <button type="button" aria-label="별">
          <IconMock kind="star" />
        </button>
        <button type="button" aria-label="말풍선">
          <IconMock kind="message" />
        </button>
        <button type="button" aria-label="메뉴">
          <IconMock kind="menu" />
        </button>
      </div>
    </header>
  );
}
