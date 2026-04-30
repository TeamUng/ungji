export type SmartAllView = "today" | "ai-match";

export type SmartAllMode = "rebuilt" | "reference";

export type WeekDayItem = {
  label: string;
  completed?: boolean;
  current?: boolean;
};

export type SubjectItem = {
  id: string;
  label: string;
  order?: number;
  active?: boolean;
  badge?: "crown";
};

export type LearningCardItem = {
  id: string;
  title: string;
  eyebrow?: string;
  subtitle: string;
  description: string;
  tone: "white" | "blue" | "mint" | "green";
  art: "rabbit" | "flame" | "science" | "balloon";
};

export type RecommendationItem = {
  title: string;
  caption: string;
  tone: "orange" | "flower";
};

export type QuickActionItem = {
  label: string;
  icon: "attendance" | "record" | "wrong";
};

export const weekDays: WeekDayItem[] = [
  { label: "월", completed: true },
  { label: "화", completed: true },
  { label: "수", current: true },
  { label: "목" },
  { label: "금" },
  { label: "토" },
  { label: "일" },
];

export const subjects: SubjectItem[] = [
  { id: "math", label: "수학", order: 1, active: true },
  { id: "korean", label: "국어", order: 2 },
  { id: "literacy", label: "문해력", order: 3 },
  { id: "hanja", label: "한자", badge: "crown" },
];

export const aiMatchCards: LearningCardItem[] = [
  {
    id: "concept",
    title: "개념별따기",
    subtitle: "국어, 사회",
    description: "핵심 개념을 짧게 확인해요",
    tone: "white",
    art: "rabbit",
  },
  {
    id: "math",
    title: "수학",
    eyebrow: "AI 기초",
    subtitle: "1단원 준비학습",
    description: "3학년 2학기 · 아이스크림\n2단원 1차시",
    tone: "blue",
    art: "flame",
  },
  {
    id: "science",
    title: "과학",
    subtitle: "1단원 단원평가",
    description: "3학년 2학기 · 아이스크림\n1단원 8차시",
    tone: "mint",
    art: "science",
  },
  {
    id: "social",
    title: "사회",
    subtitle: "옛날 사람들이 즐기던 놀이",
    description: "2단원 5차시",
    tone: "white",
    art: "balloon",
  },
];

export const recommendations: Record<SmartAllView, RecommendationItem> = {
  today: {
    title: "예절 바른 훈랑이",
    caption: "이번 주 독서",
    tone: "orange",
  },
  "ai-match": {
    title: "마을의 일 년 살이",
    caption: "이번 주 추천",
    tone: "flower",
  },
};

export const quickActions: QuickActionItem[] = [
  { label: "출석", icon: "attendance" },
  { label: "학습기록", icon: "record" },
  { label: "오답노트", icon: "wrong" },
];

export const referenceImages: Record<SmartAllView, string> = {
  today: "/smartall/reference-today.png",
  "ai-match": "/smartall/reference-ai-match.png",
};
