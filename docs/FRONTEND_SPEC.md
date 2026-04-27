# 프론트엔드 스펙 및 구현 구조

> 목적: `docs/FRONTEND_USER_FLOW.md`의 사용자 경험을 실제 프론트엔드 구조로 구현하기 위한 기술 스펙을 정리한다.
> MVP 기준은 태블릿 비율 웹 UI 목업이며, 백엔드 `POST /chat` + SSE 응답 구조와 연결 가능해야 한다.

---

## 1. 확정 스택

MVP 프론트엔드는 `frontend/` 하위에 별도 앱으로 구성한다.

확정:
- React
- Vite
- TypeScript
- CSS Modules 또는 일반 CSS
- Vercel 정적 배포

선택 이유:
- 현재 MVP는 SEO/서버 렌더링보다 채팅 상태, 선택지 클릭, SSE 수신, 메시지 렌더링이 핵심이다.
- FastAPI 백엔드와 독립적으로 mock transport를 붙여 먼저 UI 시연이 가능하다.
- T10 API가 완성된 뒤 실제 `POST /chat` + SSE 연동으로 교체하기 쉽다.
- Vercel은 Vite 정적 앱 배포를 지원하므로, 배포 플랫폼은 기존 아키텍처 방향과 동일하게 유지한다.

Next.js App Router는 장기적으로 로그인, 학부모/교사 리포트, 관리자 화면처럼 서버 렌더링과 복잡한 라우팅이 필요한 시점에 재검토한다.
현재 MVP에서는 React + Vite + TypeScript를 공식 프론트 스택으로 사용한다.

---

## 2. 앱 구조 제안

```
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  vercel.json
  src/
    main.tsx
    App.tsx
    types/
      chat.ts
      learning.ts
    api/
      chatClient.ts
      mockChatClient.ts
      sse.ts
    hooks/
      useChatSession.ts
      useCoachLayer.ts
    components/
      shell/
        TabletFrame.tsx
        SmartAllTopBar.tsx
        LearningContentShell.tsx
      today/
        TodayLearningPage.tsx
        TodayTaskBoard.tsx
        TodayTaskCard.tsx
        SubjectSidebar.tsx
      learning/
        LearningActivityPage.tsx
        ProblemStage.tsx
        ProblemContent.tsx
        AnswerArea.tsx
      coach/
        CoachLayer.tsx
        CoachAvatarButton.tsx
        CoachFloatingBubble.tsx
        CoachDrawer.tsx
        CoachDrawerHeader.tsx
        CoachMessageList.tsx
        CoachComposer.tsx
        CoachChoiceList.tsx
      messages/
        MessageRenderer.tsx
        TextMessage.tsx
        ChoicesMessage.tsx
        ImageCardMessage.tsx
        HintCardMessage.tsx
      dev/
        CaseSelector.tsx
        TouchpointDebugPanel.tsx
    data/
      mockCases.ts
      mockResponses.ts
    styles/
      app.css
  public/
    mock/
      story-01.png
      ratio-visual.png
      coach-avatar.png
```

`vercel.json`은 Vite SPA의 직접 URL 접근과 새로고침을 지원하기 위해 아래처럼 둔다.

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

---

## 3. 핵심 설계: CoachLayer

AI 코치는 개별 페이지 안에 흩어져 구현하지 않고, 공통 `CoachLayer`로 구현한다.

```tsx
<CoachLayer
  surface="floating"
  useCase="talk"
  touchpoint="tp1"
  studentId={studentId}
/>
```

```tsx
<CoachLayer
  surface="drawer"
  useCase="learning"
  touchpoint="tp4"
  studentId={studentId}
  taskId={taskId}
/>
```

`CoachLayer`의 역할:
- 오른쪽 하단 캐릭터 표시
- idle animation 적용
- 말풍선 또는 오른쪽 채팅창 표시
- 백엔드 또는 mock transport 호출
- 응답 메시지 타입별 렌더링
- 선택지 클릭 시 다음 `POST /chat` 호출

---

## 4. Coach surface 타입

```ts
export type CoachSurface = "floating" | "drawer";
```

| surface | 사용 위치 | 설명 |
|---------|----------|------|
| `floating` | TP1, TP2, TP3 1차, TP5 짧은 안내 | 캐릭터 위 말풍선과 CTA 버튼 |
| `drawer` | TP4, TP3 상세 도움, TP5 오답 복습 | 오른쪽 사이드 채팅창 |

TP별 기본 매핑:

```ts
const defaultSurfaceByTouchpoint = {
  tp1: "floating",
  tp2: "floating",
  tp3: "floating",
  tp4: "drawer",
  tp5: "floating",
} as const;
```

단, TP3과 TP5는 상황에 따라 `drawer`로 확장 가능하게 둔다.

---

## 5. 페이지 구조

### 5-1. TodayLearningPage

역할:
- 오늘 배정된 과목별 태스크 2~4개 표시
- TP1 홈화면 진입 추천 표시
- TP2 단위 학습 완료 후 다음 학습 추천 표시

포함 컴포넌트:
- `TabletFrame`
- `SmartAllTopBar`
- `SubjectSidebar`
- `TodayTaskBoard`
- `TodayTaskCard`
- `CoachLayer(surface="floating")`

예상 props:

```ts
type TodayLearningPageProps = {
  studentId: string;
  caseId: "case1" | "case2";
};
```

### 5-2. LearningActivityPage

역할:
- 실제 문제/학습 콘텐츠 목업 표시
- 오른쪽 하단 캐릭터 표시
- 캐릭터 클릭 시 TP4 채팅창 열기
- TP3 이탈 방지, TP5 종료 안내도 확장 가능

포함 컴포넌트:
- `TabletFrame`
- `LearningContentShell`
- `ProblemStage`
- `AnswerArea`
- `CoachLayer(surface="drawer")`

예상 props:

```ts
type LearningActivityPageProps = {
  studentId: string;
  taskId: string;
  caseId: "case1" | "case2";
};
```

---

## 6. API 계약

백엔드 기준 요청 구조는 `app/schemas/chat.py`의 `ChatRequest`를 따른다.

```ts
export type IncomingMessageType = "init" | "text" | "choice";

export type ChatRequest = {
  thread_id: string;
  student_id: string;
  use_case: "talk" | "learning";
  current_touchpoint: "tp1" | "tp2" | "tp3" | "tp4" | "tp5";
  message: {
    type: IncomingMessageType;
    content: string;
  };
};
```

응답 메시지 타입:

```ts
export type ResponseMessage =
  | { type: "text"; content: string }
  | { type: "choices"; items: ChoiceItem[] }
  | { type: "image_card"; image_url: string; caption: string }
  | { type: "hint_card"; steps: HintStep[] };

export type ChoiceItem = {
  id: string;
  label: string;
};

export type HintStep = {
  step: number;
  content: string;
};

export type ChatResponse = {
  thread_id: string;
  messages: ResponseMessage[];
};
```

---

## 7. SSE 수신 방식

T10은 `POST /chat` + SSE 스트리밍으로 계획되어 있다.

브라우저 기본 `EventSource`는 `POST`를 지원하지 않으므로, 프론트는 `fetch()`와 `ReadableStream` reader를 사용한다.

권장 이벤트 포맷:

```text
event: message
data: {"type":"text","content":"..."}

event: message
data: {"type":"choices","items":[{"id":"c1","label":"..."}]}

event: done
data: {"thread_id":"..."}
```

프론트 처리 방식:

```ts
await streamChat(request, {
  onMessage: (message) => appendMessage(message),
  onDone: () => setLoading(false),
  onError: (error) => showError(error),
});
```

T10 완성 전에는 `mockChatClient.ts`가 동일한 인터페이스로 mock 응답을 반환한다.

---

## 8. 상태 관리

MVP는 별도 상태관리 라이브러리 없이 React hook으로 충분하다.

```ts
type CoachState = {
  threadId: string;
  studentId: string;
  useCase: "talk" | "learning";
  touchpoint: "tp1" | "tp2" | "tp3" | "tp4" | "tp5";
  surface: "floating" | "drawer";
  isDrawerOpen: boolean;
  isLoading: boolean;
  messages: ResponseMessage[];
};
```

권장 hook:
- `useChatSession`: thread_id 생성/유지, 메시지 목록 관리, API 호출
- `useCoachLayer`: surface, drawer open/close, 캐릭터 클릭 이벤트 관리

`thread_id`는 프론트에서 UUID로 생성하고 세션 동안 유지한다.

---

## 9. 메시지 렌더링

`MessageRenderer`는 `message.type`으로 분기한다.

```tsx
function MessageRenderer({ message }: { message: ResponseMessage }) {
  switch (message.type) {
    case "text":
      return <TextMessage message={message} />;
    case "choices":
      return <ChoicesMessage message={message} />;
    case "image_card":
      return <ImageCardMessage message={message} />;
    case "hint_card":
      return <HintCardMessage message={message} />;
  }
}
```

선택지 클릭:

```ts
onChoiceClick(choice) {
  appendUserChoice(choice.label);
  sendMessage({
    type: "choice",
    content: choice.id,
  });
}
```

---

## 10. 화면별 TP 호출 흐름

### TP1

```ts
sendChat({
  use_case: "talk",
  current_touchpoint: "tp1",
  message: { type: "init", content: "" },
});
```

렌더링:
- `CoachFloatingBubble`
- text + choices

### TP2

```ts
sendChat({
  use_case: "talk",
  current_touchpoint: "tp2",
  message: { type: "init", content: "" },
});
```

렌더링:
- 완료 칭찬
- 다음 태스크 CTA

### TP3

```ts
sendChat({
  use_case: "talk",
  current_touchpoint: "tp3",
  message: { type: "init", content: "exit_attempt" },
});
```

렌더링:
- 작은 말풍선 우선
- 학생이 도움을 누르면 drawer 확장 가능

### TP4

```ts
sendChat({
  use_case: "learning",
  current_touchpoint: "tp4",
  message: { type: "init", content: "" },
});
```

렌더링:
- 캐릭터 클릭 시 `CoachDrawer` 오픈
- 막힘 원인 선택지
- 선택 후 text/image_card/hint_card 순차 렌더링

### TP5

```ts
sendChat({
  use_case: "talk",
  current_touchpoint: "tp5",
  message: { type: "init", content: "" },
});
```

렌더링:
- 오답 없음: 짧은 말풍선
- 오답 있음: 복습 CTA
- 설명이 길어지면 drawer로 확장

---

## 11. MVP 구현 순서

### FE1~FE3. 앱 초기 세팅 + 오늘의 학습 화면

- React + Vite + TypeScript 앱 생성
- `TabletFrame` 구현
- `TodayLearningPage` 구현
- `CoachAvatarButton` 구현
- `CoachFloatingBubble` 구현

완료 기준:
- 오늘의 학습 화면에서 TP1/TP2 말풍선형 추천 UI를 볼 수 있다.

### FE4~FE5. 학습 화면 + 오른쪽 코치 채팅창

- `LearningActivityPage` 구현
- `ProblemStage` 구현
- `CoachDrawer` 구현
- 오른쪽 하단 캐릭터 클릭 시 채팅창 열림/닫힘 처리

완료 기준:
- 학습 화면에서 캐릭터를 클릭하면 오른쪽 채팅창이 열린다.

### FE6. 메시지 타입 렌더링

- `text` 말풍선
- `choices` 버튼
- `image_card` 카드
- `hint_card` 단계별 카드
- 선택지 클릭 후 다음 mock 응답 연결

완료 기준:
- PRD에서 정의한 챗봇 UI 요소 4종을 모두 렌더링한다.

### FE7. mock transport 케이스 1/2 시연

- 케이스 1 TP1/TP4 mock 응답 작성
- 케이스 2 TP1/TP4 mock 응답 작성
- TP2/TP3/TP5 기본 mock 응답 작성
- 백엔드 없이 선택지 클릭 후 다음 mock 응답 연결

완료 기준:
- 백엔드 없이도 케이스 1/2의 주요 화면 흐름을 브라우저에서 볼 수 있다.

### FE8~FE9. 실제 POST /chat + SSE 연동

- T10 `POST /chat` 연결
- `fetch()` 기반 SSE 파서 구현
- `thread_id` 유지
- choice 클릭 시 실제 API 재호출
- 로딩/에러 상태 처리

완료 기준:
- T10 백엔드와 연결해 케이스 1/2 전체 흐름이 동작한다.

---

## 12. 디자인/레이아웃 기준

- 태블릿 화면 비율을 우선한다.
- 첫 화면은 랜딩 페이지가 아니라 `오늘의 학습` 메인화면이다.
- TP1/TP2는 전체 채팅창을 열지 않고 말풍선 추천으로 처리한다.
- TP4는 학습 화면 오른쪽에 채팅창을 붙인다.
- 캐릭터는 오른쪽 하단에 고정하고, idle animation은 작고 방해되지 않게 둔다.
- 선택지 버튼은 아이가 누르기 쉽게 충분한 높이와 간격을 둔다.
- 저학년 케이스는 짧은 문장과 큰 선택지를 우선한다.
- 고학년 케이스는 힌트 카드와 단계별 구조를 우선한다.

---

## 13. TODO_FRONTEND 관리 기준

프론트엔드 작업 목록은 백엔드 중심 `TODO.md`와 분리해 루트의 `TODO_FRONTEND.md`에서 관리한다.
실제 구현 이슈를 만들 때는 `TODO_FRONTEND.md`의 FE1~FE12 순서를 기준으로 쪼갠다.

```md
FE1. 프론트 앱 초기 세팅

FE2. 공통 타입과 목업 데이터

FE3. 태블릿 쉘과 오늘의 학습 화면

FE4. 학습 진행 화면

FE5. AI 코치 레이어

FE6. 메시지 타입 렌더링

FE7. mock transport 기반 케이스 시연

FE8. 실제 API 클라이언트와 SSE 연결

FE9. 프론트-백엔드 연결 합의 필요 항목

FE10. UX 상태와 예외 처리

FE11. 접근성·반응형·시각 검수

FE12. 테스트와 배포
```
