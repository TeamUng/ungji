import type { Subject } from "@/types/learning";

type SubjectSidebarProps = {
  subjects: Subject[];
  selectedSubject: Subject;
  onSelectSubject: (subject: Subject) => void;
};

export function SubjectSidebar({
  subjects,
  selectedSubject,
  onSelectSubject,
}: SubjectSidebarProps) {
  return (
    <aside className="bg-white/92 px-4 py-8 shadow-[16px_0_36px_rgba(15,23,42,0.08)]">
      <p className="mb-4 text-xs font-bold text-slate-500">과목</p>
      <div className="space-y-3">
        {subjects.map((subject) => (
          <button
            className={`subject-button ${subject === selectedSubject ? "subject-button-active" : ""}`}
            key={subject}
            type="button"
            onClick={() => onSelectSubject(subject)}
          >
            {subject}
          </button>
        ))}
      </div>
    </aside>
  );
}
