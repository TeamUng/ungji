import { IconMock } from "./IconMock";
import styles from "./SmartAllHome.module.css";

const days = [
  { label: "월", completed: true },
  { label: "화", completed: true },
  { label: "수", current: true },
  { label: "목" },
  { label: "금" },
  { label: "토" },
  { label: "일" },
];

export function DateSelector() {
  return (
    <section className={styles.dateSelector} aria-label="날짜 선택">
      <div className={styles.datePill}>
        <span className={styles.calendarMock} aria-hidden="true" />
        <strong>7월 12일</strong>
        <span>수요일</span>
      </div>

      <div className={styles.weekPill} aria-label="요일 선택">
        {days.map((day) => (
          <button
            key={day.label}
            type="button"
            className={[
              styles.dayButton,
              day.completed ? styles.completedDay : "",
              day.current ? styles.currentDay : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {day.completed && <IconMock kind="check" />}
            {day.current && <small>오늘</small>}
            <span>{day.label}</span>
          </button>
        ))}
      </div>

      <div className={styles.periodToggle} aria-label="기간 선택">
        <button type="button" className={styles.activePeriodButton}>
          오늘
        </button>
        <button type="button">이번 주</button>
      </div>
    </section>
  );
}
