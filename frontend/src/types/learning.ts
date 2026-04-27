import type { Touchpoint } from "@/types/chat";

export type CaseId = "case1" | "case2";

export type Subject = "국어" | "수학" | "사회" | "과학" | "영어";

export type GradeGroup = "lower" | "middle" | "upper";

export type Segment = "잘함+성실" | "잘함+불성실" | "못함+성실" | "못함+불성실";

export type TaskStatus = "recommended" | "ready" | "done";

export type TodayTask = {
  id: string;
  subject: Subject;
  unit: string;
  title: string;
  description: string;
  minutes: number;
  difficulty: "상" | "중" | "하";
  aiPredictedScore: number;
  status: TaskStatus;
  touchpoint?: Touchpoint;
};

export type LearningChoice = {
  id: string;
  label: string;
};

export type LearningProblem = {
  id: string;
  taskId: string;
  subject: Subject;
  title: string;
  prompt: string;
  imageUrl: string;
  imageAlt: string;
  choices: LearningChoice[];
  answerLabel: string;
  hint: string;
};

export type StudentCase = {
  id: CaseId;
  studentId: string;
  studentName: string;
  gradeLabel: string;
  gradeGroup: GradeGroup;
  segment: Segment;
  summary: string;
  recommendedTaskId: string;
  todayTasks: TodayTask[];
  problem: LearningProblem;
  wrongAnswerSummary: {
    total: number;
    done: number;
  };
};
