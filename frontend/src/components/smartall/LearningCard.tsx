import type { LearningCardItem } from "@/data/smartallMockData";
import styles from "./SmartAllHome.module.css";

type LearningCardProps = {
  card: LearningCardItem;
};

export function LearningCard({ card }: LearningCardProps) {
  return (
    <article
      className={`${styles.learningCard} ${styles[card.tone]} ${
        styles[`${card.id}Card`]
      }`}
    >
      <div className={styles.learningCardCopy}>
        {card.eyebrow && <span className={styles.cardEyebrow}>{card.eyebrow}</span>}
        {card.id === "math" && (
          <span className={styles.difficultyBadge}>이번 단원 AI 예상 이해도 어려움</span>
        )}
        <h2>
          {card.title} <span aria-hidden="true">★</span>
        </h2>
        <strong>{card.subtitle}</strong>
        <p>{card.description}</p>
      </div>
      <span
        className={`${styles.cardArt} ${styles[`${card.art}Art`]}`}
        aria-hidden="true"
      >
        <span className={styles.cardArtDetailOne} />
        <span className={styles.cardArtDetailTwo} />
        <span className={styles.cardArtDetailThree} />
      </span>
    </article>
  );
}
