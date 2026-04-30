import type { SmartAllView } from "@/data/smartallMockData";
import { quickActions, recommendations } from "@/data/smartallMockData";
import { QuickActionButtons } from "./QuickActionButtons";
import styles from "./SmartAllHome.module.css";

type RecommendationPanelProps = {
  view: SmartAllView;
};

export function RecommendationPanel({ view }: RecommendationPanelProps) {
  const recommendation = recommendations[view];

  return (
    <aside className={styles.recommendationPanel} aria-label="추천 학습 패널">
      <h2>
        <span className={styles.recommendMedal} aria-hidden="true" />
        김웅진님을 위한 추천
      </h2>

      <article className={styles.bookCarousel}>
        <button type="button" className={styles.carouselButton} aria-label="이전 추천">
          ‹
        </button>
        <div className={`${styles.bookCover} ${styles[recommendation.tone]}`}>
          <span className={styles.bookDecorOne} aria-hidden="true" />
          <span className={styles.bookDecorTwo} aria-hidden="true" />
          <span className={styles.bookCharacter} aria-hidden="true" />
          <strong>{recommendation.title}</strong>
          <em>{recommendation.caption}</em>
        </div>
        <button type="button" className={styles.carouselButton} aria-label="다음 추천">
          ›
        </button>
      </article>

      <div className={styles.paginationDots} aria-hidden="true">
        <span className={styles.activeDot} />
        <span />
      </div>

      <article className={styles.challengeCard} aria-label="올도전 카드">
        <div>
          <strong>올도전</strong>
          <span>나의 별 {view === "today" ? "17,250" : "12,750"}</span>
        </div>
        <div className={styles.challengeBox} aria-hidden="true">
          <span>?</span>
        </div>
      </article>

      <QuickActionButtons actions={quickActions} />
    </aside>
  );
}
