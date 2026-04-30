export const chatbotSuggestions = {
  "learning-card": "오늘은 수의 크기를 비교하는 공부야. 같이 해볼래?",
  "learning-start": "바로 수학 학습을 시작해볼까?",
  "subject-math": "수학부터 풀어보면 오늘 학습을 빠르게 시작할 수 있어.",
  "subject-korean": "국어 공부도 이어서 해볼까?",
  "subject-literacy": "문해력은 글을 이해하는 힘을 키워줘!",
  "subject-hanja": "한자도 조금씩 익히면 어휘력이 좋아져.",
  "subject-science": "과학은 그림과 표를 같이 보면 더 쉽게 풀 수 있어.",
  "subject-social": "사회는 이야기처럼 읽어보면 흐름이 잘 보여.",
  "recommended-book": "오늘의 추천 책도 잠깐 읽어볼래?",
  "challenge-card": "별을 모으는 도전도 해볼 수 있어!",
  attendance: "출석 체크하고 오늘 학습을 시작해보자.",
  "study-record": "내가 얼마나 공부했는지 확인해볼까?",
  "wrong-note": "전에 틀린 문제를 다시 보면 더 오래 기억할 수 있어.",
  "problem-board": "문제를 읽다가 막히면 뽀롱쌤이 한 줄씩 도와줄게.",
  "help-button": "힌트가 필요하면 여기서 바로 도움을 열 수 있어.",
  "complete-button": "다 풀었다면 채점하고 다음 학습으로 가보자.",
  "exit-button": "나가기 전에 딱 한 문제만 같이 확인해볼까?",
  "completion-card": "방금 끝낸 학습을 짧게 돌아보고 다음 선택을 해보자.",
} as const;

export type InteractionZoneId = keyof typeof chatbotSuggestions;

export type InteractionZoneType =
  | "content"
  | "primary-action"
  | "subject"
  | "recommendation"
  | "quick-menu";
