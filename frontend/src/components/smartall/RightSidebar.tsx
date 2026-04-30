import { InteractionZone } from "@/components/chatbot/InteractionZone";
import { IconMock } from "./IconMock";
import styles from "./SmartAllHome.module.css";

const quickMenus = [
  { id: "attendance" as const, label: "출석", icon: "attendance" as const },
  { id: "study-record" as const, label: "학습기록", icon: "record" as const },
  { id: "wrong-note" as const, label: "오답노트", icon: "wrong" as const },
];

export function RightSidebar() {
  return (
    <aside className={styles.rightSidebar} aria-label="추천과 빠른 메뉴">
      <h2>
        <span aria-hidden="true" />
        김웅진님을 위한 추천
      </h2>

      <InteractionZone
        id="recommended-book"
        label="추천 독서"
        type="recommendation"
        className={styles.recommendedBookZone}
      >
        <article className={styles.bookPanel}>
          <button type="button" className={styles.carouselButton} aria-label="이전 추천">
            ‹
          </button>
          <div className={styles.bookCover}>
            <IconMock kind="book" />
            <strong>예절 바른 어린이</strong>
            <em>이번 주 독서</em>
          </div>
          <button type="button" className={styles.carouselButton} aria-label="다음 추천">
            ›
          </button>
        </article>
      </InteractionZone>

      <div className={styles.slideIndicator} aria-hidden="true">
        <span className={styles.activeIndicator} />
        <span />
      </div>

      <InteractionZone
        id="challenge-card"
        label="올도전"
        type="recommendation"
        className={styles.challengeZone}
      >
        <article className={styles.challengeCard}>
          <div>
            <strong>올도전</strong>
            <span>나의 별 17,250</span>
          </div>
          <div className={styles.treasureBox} aria-hidden="true">
            ★
          </div>
        </article>
      </InteractionZone>

      <div className={styles.quickMenu} aria-label="빠른 메뉴">
        {quickMenus.map((menu) => (
          <InteractionZone
            key={menu.id}
            id={menu.id}
            label={menu.label}
            type="quick-menu"
            className={styles.quickMenuZone}
          >
            <button type="button">
              <IconMock kind={menu.icon} />
              <span>{menu.label}</span>
            </button>
          </InteractionZone>
        ))}
      </div>
    </aside>
  );
}
