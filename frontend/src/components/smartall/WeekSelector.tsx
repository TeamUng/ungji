import type { SmartAllView } from "@/data/smartallMockData";
import { weekDays } from "@/data/smartallMockData";
import styles from "./SmartAllHome.module.css";

type WeekSelectorProps = {
  view: SmartAllView;
};

export function WeekSelector({ view }: WeekSelectorProps) {
  const dateLabel = view === "today" ? "7월 12일" : "10월 1일";

  return (
    <section className={styles.weekSelector} aria-label="이번 주 학습 날짜">
      <div className={styles.datePill}>
        <span className={styles.calendarIcon} aria-hidden="true" />
        <strong>{dateLabel}</strong>
        <span>수요일</span>
      </div>

      <div className={styles.weekPill} aria-label="요일 선택">
        {weekDays.map((day) => (
          <button
            key={day.label}
            type="button"
            className={[
              styles.dayButton,
              day.completed ? styles.completedDay : "",
              day.current ? styles.currentDay : "",
            ].join(" ")}
          >
            {day.current && <small>오늘</small>}
            <span>{day.label}</span>
          </button>
        ))}
      </div>

      <div className={styles.weekActionGroup}>
        <button type="button" className={styles.todayButton}>
          오늘
        </button>
        <button type="button" className={styles.weekButton}>
          이번 주
        </button>
      </div>
    </section>
  );
}
