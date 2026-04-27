import { caseList } from "@/data/mockCases";
import type { CaseId } from "@/types/learning";

type CaseSelectorProps = {
  activeCaseId: CaseId;
  onCaseChange: (caseId: CaseId) => void;
};

export function CaseSelector({ activeCaseId, onCaseChange }: CaseSelectorProps) {
  return (
    <div className="case-selector" aria-label="시연 케이스 선택">
      {caseList.map((studentCase) => (
        <button
          className={studentCase.id === activeCaseId ? "case-tab case-tab-active" : "case-tab"}
          key={studentCase.id}
          type="button"
          onClick={() => onCaseChange(studentCase.id)}
        >
          {studentCase.id === "case1" ? "케이스 1" : "케이스 2"}
        </button>
      ))}
    </div>
  );
}
