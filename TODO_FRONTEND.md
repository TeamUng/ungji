# TODO_FRONTEND

프론트엔드 전용 작업 목록입니다.

백엔드/그래프/API 작업은 `TODO.md`에서 관리하고, 프론트 유저 흐름과 구현 작업은 이 문서에서 관리합니다.

## 구현 목표

React + Vite + TypeScript + Tailwind CSS 기반 웹 UI로 스마트올 태블릿 환경의 AI 학습코치 경험을 시연한다.

핵심 경험:
- `오늘의 학습` 화면에서 AI 코치가 학생 상태에 맞는 학습을 말풍선으로 추천한다.
- 학습 화면 오른쪽 하단에 AI 코치 캐릭터가 떠 있다.
- 학생이 캐릭터를 누르면 오른쪽 채팅창이 열리고, 막힘 원인 선택지와 단계별 도움을 제공한다.
- 케이스 1(저학년 국어)과 케이스 2(고학년 수학)를 브라우저에서 처음부터 끝까지 시연할 수 있다.

참고 문서:
- 유저 흐름: `docs/FRONTEND_USER_FLOW.md`
- 구현 스펙: `docs/FRONTEND_SPEC.md`
- 백엔드 API 구조: `docs/ARCHITECTURE_REVIEW.md`, `docs/STATE_DESIGN.md`
- 제품 요구사항: `docs/PRD.md`

---

## 현재 결정 사항

| 항목 | 결정 |
|------|------|
| 프론트 스택 | React + Vite + TypeScript + Tailwind CSS |
| 배포 | Vercel 정적 배포 |
| 앱 위치 | `frontend/` |
| 1차 구현 방식 | mock transport로 UI 선행 구현 |
| 실제 API 연결 | T10 `POST /chat` + SSE 완료 후 연동 |
| 주요 UI 패턴 | 오늘의 학습 화면 + AI 코치 플로팅 말풍선 + 오른쪽 채팅창 |

---

## FE0. 프론트 기획/스펙 정리

**담당 파일**: `docs/FRONTEND_USER_FLOW.md`, `docs/FRONTEND_SPEC.md`, `docs/ARCHITECTURE_REVIEW.md`, `TODO_FRONTEND.md`

- [x] 프론트 유저 흐름 문서 작성
- [x] 프론트 구현 스펙 문서 작성
- [x] 프론트 스택을 React + Vite + TypeScript + Tailwind CSS on Vercel로 확정
- [x] 기존 `TODO.md`와 프론트 TODO 분리
- [ ] 디자인 기준 확정 — 캐릭터 에셋, 색상, 말풍선 형태, 채팅창 폭
- [ ] 태블릿 기준 해상도/비율 확정
- [ ] 케이스 1/2에서 사용할 목업 이미지 에셋 확정
- [ ] **완료 기준**: 기획/디자인/개발자가 같은 화면 흐름을 기준으로 구현을 시작할 수 있음

---

## FE1. 프론트 앱 초기 세팅

**담당 파일**: `frontend/`

- [ ] `frontend/` React + Vite + TypeScript 앱 생성 후 Tailwind CSS 적용
- [ ] Tailwind CSS 설치 및 설정 (`tailwind.config.ts`, `postcss.config.js`)
- [ ] `frontend/vercel.json` 추가 — SPA rewrite 설정
- [ ] `frontend/.env.example` 추가 — `VITE_CHAT_API_BASE_URL`, mock 사용 플래그
- [ ] `frontend/src/styles/app.css`에 Tailwind base/components/utilities 연결
- [ ] 절대경로 alias 설정 검토 (`@/components`, `@/api` 등)
- [ ] `package.json` scripts 정리 — `dev`, `build`, `preview`, `typecheck`
- [ ] README 또는 프론트 실행 문서 추가
- [ ] **완료 기준**: `cd frontend && npm install && npm run dev`로 빈 앱 실행 가능

---

## FE2. 공통 타입과 목업 데이터

**담당 파일**: `frontend/src/types/`, `frontend/src/data/`

- [ ] `ChatRequest`, `ChatResponse`, `ResponseMessage` 타입 정의
- [ ] `Touchpoint`, `UseCase`, `IncomingMessageType` 타입 정의
- [ ] `TodayTask`, `StudentCase`, `LearningProblem` 타입 정의
- [ ] 케이스 1 학생 mock 데이터 작성
- [ ] 케이스 2 학생 mock 데이터 작성
- [ ] 오늘의 학습 태스크 2~4개 mock 데이터 작성
- [ ] 국어 짧은 글 읽기 문제 mock 데이터 작성
- [ ] 수학 비율/비례식 문제 mock 데이터 작성
- [ ] TP1~TP5 mock 응답 데이터 작성
- [ ] **완료 기준**: 백엔드 없이도 케이스 1/2 화면에 필요한 데이터가 모두 준비됨

---

## FE3. 태블릿 쉘과 오늘의 학습 화면

**담당 파일**: `frontend/src/components/shell/`, `frontend/src/components/today/`

- [ ] `TabletFrame` 구현 — 태블릿 비율 고정/반응형 컨테이너
- [ ] `SmartAllTopBar` 구현 — 목업 상단 내비게이션
- [ ] `TodayLearningPage` 구현
- [ ] `SubjectSidebar` 구현 — 과목 목록/선택 상태
- [ ] `TodayTaskBoard` 구현 — 오늘 배정 태스크 2~4개 표시
- [ ] `TodayTaskCard` 구현 — 과목, 단원, 예상 시간, 진행 상태 표시
- [ ] 케이스 1/2 전환 시 오늘의 학습 내용 변경
- [ ] 태스크 카드 클릭 시 학습 화면으로 이동
- [ ] **완료 기준**: 오늘의 학습 화면에서 과목별 태스크와 기본 학습 이동 흐름 확인 가능

---

## FE4. 학습 진행 화면

**담당 파일**: `frontend/src/components/learning/`

- [ ] `LearningActivityPage` 구현
- [ ] `LearningContentShell` 구현 — 문제 영역 + 코치 레이어가 공존하는 레이아웃
- [ ] `ProblemStage` 구현 — 문제 지문/이미지/보기 표시
- [ ] `ProblemContent` 구현 — 케이스별 콘텐츠 렌더링
- [ ] `AnswerArea` 구현 — 선택/입력/제출 목업
- [ ] 문제 풀이 중 이탈 시도 트리거 목업 구현
- [ ] 단위 학습 완료 트리거 목업 구현
- [ ] 오늘 학습 종료 트리거 목업 구현
- [ ] **완료 기준**: 학습 화면에서 TP3/TP4/TP5를 수동으로 발생시킬 수 있음

---

## FE5. AI 코치 레이어

**담당 파일**: `frontend/src/components/coach/`, `frontend/src/hooks/useCoachLayer.ts`

- [ ] `CoachLayer` 구현 — 모든 화면 위에 공통으로 얹히는 AI 코치 레이어
- [ ] `CoachAvatarButton` 구현 — 오른쪽 하단 캐릭터 버튼
- [ ] 캐릭터 idle animation 구현 — 작고 방해되지 않는 움직임
- [ ] `CoachFloatingBubble` 구현 — TP1/TP2/TP3/TP5 짧은 말풍선
- [ ] `CoachDrawer` 구현 — 오른쪽 사이드 채팅창
- [ ] `CoachDrawerHeader` 구현 — 제목, 닫기 버튼, 상태 표시
- [ ] `CoachMessageList` 구현 — 메시지 목록 스크롤
- [ ] `CoachComposer` 구현 — teach-back 또는 자유 입력용
- [ ] `CoachChoiceList` 구현 — 선택지 버튼 묶음
- [ ] `useCoachLayer` 구현 — drawer 열림/닫힘, surface 전환
- [ ] TP별 기본 surface 매핑 구현
- [ ] **완료 기준**: 캐릭터 버튼, 플로팅 말풍선, 오른쪽 채팅창이 같은 `CoachLayer`에서 동작

---

## FE6. 메시지 타입 렌더링

**담당 파일**: `frontend/src/components/messages/`

- [ ] `MessageRenderer` 구현 — `message.type` 기준 분기
- [ ] `TextMessage` 구현 — AI 말풍선
- [ ] `ChoicesMessage` 구현 — 선택지 버튼
- [ ] `ImageCardMessage` 구현 — 이미지 카드 + 캡션
- [ ] `HintCardMessage` 구현 — 단계별 힌트 카드
- [ ] 사용자 선택/입력 메시지 렌더링 방식 정의
- [ ] 선택지 클릭 시 사용자 선택 메시지 추가
- [ ] 긴 문장/긴 선택지 태블릿 폭에서 줄바꿈 검증
- [ ] **완료 기준**: PRD의 챗봇 UI 요소 4종을 모두 렌더링 가능

---

## FE7. mock transport 기반 케이스 시연

**담당 파일**: `frontend/src/api/mockChatClient.ts`, `frontend/src/data/mockResponses.ts`

- [ ] mock chat client 인터페이스 정의 — 실제 API client와 동일한 함수 시그니처
- [ ] TP1 케이스 1 응답 작성 — 저학년 국어 짧은 시작 추천
- [ ] TP1 케이스 2 응답 작성 — 고학년 수학 비율 약점 보완 추천
- [ ] TP2 응답 작성 — 단위 학습 완료 후 다음 학습 추천
- [ ] TP3 응답 작성 — 이탈 방지 말풍선/채팅 흐름
- [ ] TP4 케이스 1 응답 작성 — 국어 막힘 원인 4종
- [ ] TP4 케이스 2 응답 작성 — 수학 막힘 원인 4종
- [ ] TP5 응답 작성 — 오답 없음/오답 있음/복습 미완료 분기
- [ ] 케이스 1 전체 흐름 수동 시연
- [ ] 케이스 2 전체 흐름 수동 시연
- [ ] **완료 기준**: 백엔드 없이 브라우저에서 PRD 케이스 1·2의 핵심 흐름 시연 가능

---

## FE8. 실제 API 클라이언트와 SSE 연결

**담당 파일**: `frontend/src/api/chatClient.ts`, `frontend/src/api/sse.ts`, `frontend/src/hooks/useChatSession.ts`

**의존**: 백엔드 T10 `POST /chat` 엔드포인트

- [ ] `VITE_CHAT_API_BASE_URL` 환경변수 사용
- [ ] `thread_id` 생성 및 세션 내 유지
- [ ] `ChatRequest` builder 구현
- [ ] TP1/TP2/TP3/TP5 → `use_case="talk"` 매핑
- [ ] TP4 → `use_case="learning"` 매핑
- [ ] `current_touchpoint` 전달
- [ ] `student_id` 전달
- [ ] `message.type="init"` 요청 처리
- [ ] `message.type="choice"` 요청 처리
- [ ] `message.type="text"` 요청 처리
- [ ] `fetch()` + `ReadableStream` 기반 SSE 파서 구현
- [ ] `event: message` 파싱
- [ ] `event: done` 파싱
- [ ] `event: error` 파싱
- [ ] 백엔드가 `ChatResponse.messages[]`를 한 번에 보내는 경우도 호환 처리
- [ ] 요청 중복 방지를 위한 loading/abort 처리
- [ ] API 에러 메시지 UI 처리
- [ ] 네트워크 실패 시 재시도 또는 mock fallback 정책 결정
- [ ] **완료 기준**: T10 백엔드와 연결해 TP1/TP4 실제 응답을 화면에 렌더링

---

## FE9. 프론트-백엔드 연결 합의 필요 항목

**담당 파일**: `docs/FRONTEND_SPEC.md`, 백엔드 T10 구현 파일

- [ ] SSE 이벤트 포맷 확정
  - 권장: `event: message`, `event: done`, `event: error`
- [ ] 선택지 클릭 시 `message.content`에 `choice.id`를 보낼지 `choice.label`을 보낼지 확정
  - 권장: `choice.id`
- [ ] TP4 첫 호출 시 `message.type="init"`으로 막힘 원인 선택지를 받을지 확정
- [ ] teach-back 입력은 `message.type="text"`로 보낼지 확정
- [ ] 로컬 개발 CORS 또는 Vite proxy 방식 확정
  - 권장: 로컬은 Vite proxy, 배포는 백엔드 CORS 허용 또는 동일 도메인 프록시
- [ ] Vercel 프론트 URL과 FastAPI 백엔드 URL 환경변수/허용 origin 정리
- [ ] 이미지 카드의 `image_url` 기준 확정
  - 권장: 프론트 public asset 또는 백엔드 정적 asset 중 하나로 통일
- [ ] 에러 응답 형식 확정
- [ ] **완료 기준**: FE8 실제 API 연결 시 프론트/백엔드 간 임의 해석 없이 구현 가능

---

## FE10. UX 상태와 예외 처리

**담당 파일**: `frontend/src/components/coach/`, `frontend/src/hooks/`

- [ ] 코치 응답 로딩 상태
- [ ] 스트리밍 중 메시지 순차 표시
- [ ] 빈 응답 처리
- [ ] API 오류 처리
- [ ] 존재하지 않는 student_id 오류 처리
- [ ] 선택지 클릭 후 중복 클릭 방지
- [ ] drawer 닫기/다시 열기 시 메시지 유지
- [ ] 케이스 변경 시 세션 초기화
- [ ] thread_id 리셋 버튼 또는 개발용 초기화 버튼
- [ ] **완료 기준**: 데모 중 흔한 오류 상황에서도 화면이 깨지지 않음

---

## FE11. 접근성·반응형·시각 검수

**담당 파일**: `frontend/src/styles/`, 각 UI 컴포넌트

- [ ] 태블릿 기준 화면 비율 검수
- [ ] 작은 데스크톱/큰 태블릿 폭 검수
- [ ] 버튼 터치 영역 충분한지 확인
- [ ] 텍스트가 버튼/카드 밖으로 넘치지 않는지 확인
- [ ] 채팅창이 문제 지문을 과도하게 가리지 않는지 확인
- [ ] 키보드 포커스 이동 기본 동작 확인
- [ ] 이미지 카드 대체 텍스트 처리
- [ ] 캐릭터 animation이 과하지 않은지 확인
- [ ] **완료 기준**: 케이스 1·2를 태블릿 비율에서 무리 없이 읽고 조작 가능

---

## FE12. 테스트와 배포

**담당 파일**: `frontend/`, Vercel 설정

- [ ] `npm run build` 통과
- [ ] `npm run typecheck` 통과
- [ ] mock transport 기준 케이스 1 수동 테스트
- [ ] mock transport 기준 케이스 2 수동 테스트
- [ ] 실제 API 기준 케이스 1 수동 테스트
- [ ] 실제 API 기준 케이스 2 수동 테스트
- [ ] Vercel preview deployment 확인
- [ ] Vercel 환경변수 설정 확인
- [ ] 배포 URL에서 새로고침/직접 접근 확인
- [ ] **완료 기준**: Vercel preview URL에서 케이스 1·2 핵심 흐름 시연 가능

---

## 구현 순서 추천

1. FE1 앱 초기 세팅
2. FE2 공통 타입과 목업 데이터
3. FE3 오늘의 학습 화면
4. FE5 AI 코치 레이어
5. FE6 메시지 타입 렌더링
6. FE4 학습 진행 화면
7. FE7 mock transport 케이스 시연
8. FE9 프론트-백엔드 연결 합의
9. FE8 실제 API/SSE 연결
10. FE10~FE12 UX 보완, 검수, 배포
