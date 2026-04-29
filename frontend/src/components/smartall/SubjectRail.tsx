import { subjects } from "@/data/smartallMockData";
import styles from "./SmartAllHome.module.css";

export function SubjectRail() {
  return (
    <aside className={styles.subjectRail} aria-label="오늘의 과목 탭">
      {subjects.map((subject) => (
        <button
          key={subject.id}
          type="button"
          className={subject.active ? styles.activeSubject : ""}
        >
          <span className={styles.subjectBadge}>
            {subject.badge === "crown" ? "♛" : subject.order}
          </span>
          <strong>{subject.label}</strong>
        </button>
      ))}
    </aside>
  );
}
