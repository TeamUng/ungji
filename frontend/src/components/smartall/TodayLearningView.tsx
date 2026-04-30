import { RecommendationPanel } from "./RecommendationPanel";
import { SubjectRail } from "./SubjectRail";
import styles from "./SmartAllHome.module.css";

export function TodayLearningView() {
  return (
    <section className={styles.todayLayout} aria-label="오늘의 학습 홈">
      <SubjectRail />

      <article className={styles.todayMainCard} aria-label="수학 학습 카드">
        <div className={styles.mathCopy}>
          <h1>
            수학 <span aria-hidden="true">★</span>
          </h1>
          <p>1만큼 더 큰수와 1만큼 더 작은 수를 알아볼까요</p>
          <small>1학년 1학기 · 2단원 1차시</small>
        </div>

        <div className={styles.floatingNumberSix}>6</div>
        <div className={styles.floatingNumberEight}>8</div>
        <div className={styles.cloudShape} aria-hidden="true" />
        <div className={styles.crocodileArt} aria-label="악어 캐릭터 일러스트">
          <span className={styles.crocodileSun} />
          <span className={styles.crocodileEyeLeft} />
          <span className={styles.crocodileEyeRight} />
          <span className={styles.crocodileMouth} />
          <span className={styles.crocodileTeeth}>1 2 3 4 5</span>
          <span className={styles.crocodileLowerTeeth}>7 9</span>
          <span className={styles.crocodileNoseDotOne} />
          <span className={styles.crocodileNoseDotTwo} />
          <span className={styles.crocodilePencil} />
          <span className={styles.crocodileSparkle} />
          <span className={styles.crocodileBody} />
        </div>

        <button type="button" className={styles.studyStartButton}>
          <span aria-hidden="true">▶</span>
          학습시작
        </button>
      </article>

      <RecommendationPanel view="today" />
    </section>
  );
}
