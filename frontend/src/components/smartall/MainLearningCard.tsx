import { InteractionZone } from "@/components/chatbot/InteractionZone";
import styles from "./SmartAllHome.module.css";

export function MainLearningCard() {
  return (
    <InteractionZone
      id="learning-card"
      label="수학 학습 카드"
      type="content"
      className={styles.learningCardZone}
    >
      <article className={styles.mainLearningCard} aria-label="수학 학습 카드">
        <div className={styles.cardGridPattern} aria-hidden="true" />

        <div className={styles.learningCopy}>
          <h1>
            수학 <span aria-hidden="true">별</span>
          </h1>
          <p>1만큼 더 큰수와 1만큼 더 작은 수를 알아볼까요</p>
          <small>1학년 1학기 · 2단원 1차시</small>
        </div>

        <div className={styles.numberCardSix}>6</div>
        <div className={styles.numberCardEight}>8</div>

        <div className={styles.crocodileScene} aria-label="악어 캐릭터 그림">
          <div className={styles.skyShape} />
          <div className={styles.crocodileBody}>
            <span className={styles.crocodileEyeLeft} />
            <span className={styles.crocodileEyeRight} />
            <span className={styles.crocodileMouth} />
            <span className={styles.crocodileTeeth}>1 2 3 4 5</span>
            <span className={styles.crocodileLowerTeeth}>7 9</span>
          </div>
          <div className={styles.pencilMock} />
        </div>

        <InteractionZone
          id="learning-start"
          label="학습시작"
          type="primary-action"
          className={styles.learningStartZone}
        >
          <button type="button" className={styles.studyStartButton}>
            <span aria-hidden="true" />
            학습시작
          </button>
        </InteractionZone>
      </article>
    </InteractionZone>
  );
}
