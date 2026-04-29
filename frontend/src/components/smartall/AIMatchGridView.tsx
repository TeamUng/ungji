import { aiMatchCards } from "@/data/smartallMockData";
import { LearningCard } from "./LearningCard";
import { RecommendationPanel } from "./RecommendationPanel";
import styles from "./SmartAllHome.module.css";

export function AIMatchGridView() {
  return (
    <section className={styles.aiLayout} aria-label="AI맞춤 카드형 홈">
      <div className={styles.aiCardGrid}>
        {aiMatchCards.map((card) => (
          <LearningCard key={card.id} card={card} />
        ))}
      </div>

      <RecommendationPanel view="ai-match" />
    </section>
  );
}
