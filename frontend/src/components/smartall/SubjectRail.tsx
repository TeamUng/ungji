import { InteractionZone } from "@/components/chatbot/InteractionZone";
import type { InteractionZoneId } from "@/components/chatbot/chatbotSuggestions";
import styles from "./SmartAllHome.module.css";

const subjects: Array<{
  id: InteractionZoneId;
  label: string;
  order: number;
  active?: boolean;
}> = [
  { id: "subject-math", label: "수학", order: 1, active: true },
  { id: "subject-korean", label: "국어", order: 2 },
  { id: "subject-literacy", label: "문해력", order: 3 },
  { id: "subject-hanja", label: "한자", order: 4 },
];

export function SubjectRail() {
  return (
    <aside className={styles.subjectRail} aria-label="과목 선택">
      {subjects.map((subject) => (
        <InteractionZone
          key={subject.id}
          id={subject.id}
          label={subject.label}
          type="subject"
          className={styles.subjectZone}
        >
          <button
            type="button"
            className={subject.active ? styles.activeSubjectButton : ""}
          >
            <span>{subject.order}</span>
            <strong>{subject.label}</strong>
          </button>
        </InteractionZone>
      ))}
    </aside>
  );
}
