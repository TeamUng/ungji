# 워크로그: 2026-04-29 T11 프론트 TP 흐름 보완

## 기본 정보

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-04-29 |
| 담당자 | Codex |
| 브랜치 | feature/T11-frontend |
| TODO 항목 | T11. 챗봇 UI |
| 작업 성격 | `FRONTEND_USER_FLOW.md` 기준 TP 흐름 보완 |

---

## 한 줄 요약

> 기존 T11 화면 목업을 “보이는 화면”에서 “선택지에 따라 대화가 이어지는 mock 챗봇 흐름”으로 보완했습니다.

---

## 왜 했나요?

이전 구현은 TP1~TP5 화면 형태는 갖췄지만, 채팅 선택지를 눌렀을 때 다음 코치 응답이 실제로 분기되지 않았습니다.

이번 작업의 목표는 아래였습니다.

- 학생 선택 말풍선이 채팅창에 누적되게 만들기
- TP4 도움 요청에서 선택지별로 다른 코치 응답을 보여주기
- 수학 케이스에서 teach-back 입력 흐름 만들기
- TP3, TP5처럼 말풍선으로 시작했다가 필요하면 채팅창으로 이어지는 흐름 보완하기
- `/` 학생 화면과 `/tp-demo` 내부 검수 화면을 분리하기
- T10 이후 실제 `/chat` 또는 SSE에 연결할 adapter 구조를 미리 나누기

---

## 구현 내용

### 1. 누적 대화 구조

`SmartAllCoachApp`의 채팅 표시 방식을 바꿨습니다.

이전에는 현재 `stepId`에 맞는 메시지 배열을 한 번에 보여줬습니다.

이제는 `ChatTurn[]` 형태로 대화를 쌓습니다.

- 코치 메시지: `role: "coach"`
- 학생 선택/입력: `role: "student"`

그래서 선택지를 누르면 먼저 학생 말풍선이 추가되고, 그 다음 mock adapter가 만든 코치 응답이 순서대로 붙습니다.

### 2. 선택지별 mock 응답 분기

`frontend/src/lib/mock-chat.ts`를 재구성했습니다.

케이스 1 국어 TP4 분기:

- `글이 너무 길어`
- `무슨 상황인지 모르겠어`
- `주인공 마음을 모르겠어`
- `그냥 하기 싫어`

케이스 2 수학 TP4 분기:

- `비율 뜻이 헷갈려요`
- `어떤 수끼리 비교할지 모르겠어요`
- `식을 어떻게 세울지 모르겠어요`
- `계산하다가 틀렸어요`

각 선택지는 서로 다른 `text`, `choices`, `image_card`, `hint_card` 조합으로 응답합니다.

### 3. teach-back 입력

수학 케이스에서 `식을 어떻게 세울지 모르겠어요`를 선택하면 단계별 힌트 뒤에 짧은 입력창이 나옵니다.

학생이 자기 말로 설명을 입력하면 `message.type = "text"`로 mock adapter에 전달됩니다.
mock adapter는 답변 안에 `3배`, `15`, `2`, `6` 같은 핵심 흐름이 있는지 보고 후속 격려 메시지를 반환합니다.

### 4. TP3, TP5 흐름 보완

TP3:

- 먼저 작은 말풍선으로 이탈을 붙잡습니다.
- `도움 받고 풀기` 또는 비슷한 도움 선택을 누르면 오른쪽 채팅창이 열립니다.

TP5:

- 저학년 국어는 오답이 없는 짧은 마무리 말풍선으로 종료합니다.
- 고학년 수학은 오답이 남은 상태를 말풍선으로 안내합니다.
- `오답 복습하기`를 누르면 채팅창에서 단계별 복습 힌트를 보여줍니다.

### 5. adapter 분리

프론트 타입에 `ChatAdapter` 인터페이스를 추가했습니다.

- `mockChatAdapter`: 현재 mock 검수용
- `liveChatAdapter`: T10 이후 실제 `/chat` 또는 SSE 응답 연결용

`liveChatAdapter`는 JSON 응답과 `text/event-stream` 응답을 모두 처리할 수 있게 골격을 만들었습니다.
단, 실제 `/chat` API가 아직 없으므로 실제 서버 연동 검증은 다음 단계로 남겼습니다.

### 6. 화면 분리

학생 화면과 내부 검수 화면을 분리했습니다.

- `/`: 학생이 보는 자연 흐름. 데모 컨트롤 없음.
- `/tp-demo`: mock 학생 드롭다운과 TP 전환 버튼이 있는 내부 검수 화면.

---

## 변경 파일

| 파일 | 설명 |
|------|------|
| `frontend/src/components/smartall/SmartAllCoachApp.tsx` | 누적 대화, 선택지 처리, teach-back, TP 전환 흐름 구현 |
| `frontend/src/lib/mock-chat.ts` | 케이스·TP·선택지별 mock 응답 분기 |
| `frontend/src/lib/live-chat.ts` | 실제 `/chat` 및 SSE 연결용 adapter 골격 |
| `frontend/src/types/chat.ts` | `ChatAdapter`, `ChatTurn` 등 프론트 내부 타입 추가 |
| `frontend/src/app/tp-demo/page.tsx` | 내부 검수용 TP 데모 경로 추가 |
| `frontend/src/app/globals.css` | 학생 말풍선, teach-back 입력창, mock 학생 드롭다운 스타일 |
| `frontend/README.md` | `/`와 `/tp-demo` 사용법 및 확인 포인트 갱신 |
| `TODO.md` | 완료된 T11 세부 항목 체크 |

---

## 검증 결과

### 명령어 검증

```powershell
cd frontend
npm run lint
npm run build
```

결과:

| 검증 | 결과 |
|------|------|
| `npm run lint` | 통과 |
| `npm run build` | 통과 |

### 브라우저 검증

이미 떠 있던 `http://localhost:3000` Next dev 서버를 기준으로 headless Chrome과 DevTools Protocol을 사용해 확인했습니다.

| 검증 항목 | 결과 |
|------|------|
| `/tp-demo` 내부 검수 컨트롤 표시 | 통과 |
| TP4 국어 초기 선택지 4개 표시 | 통과 |
| 국어 `글이 너무 길어` 선택 후 학생 말풍선 + 힌트 카드 표시 | 통과 |
| 수학 케이스 전환 | 통과 |
| TP4 수학 초기 선택지 4개 표시 | 통과 |
| 수학 `식을 어떻게 세울지 모르겠어요` 선택 후 teach-back 입력창 표시 | 통과 |
| teach-back 제출 후 후속 코치 응답 표시 | 통과 |
| `/` 학생 화면에서 데모 컨트롤 숨김 | 통과 |
| TP3 말풍선 후 상세 채팅창 전환 | 통과 |
| TP5 오답 복습 말풍선 후 채팅창 전환 | 통과 |

화면 스크린샷은 임시 검증 산출물로 아래에 생성했습니다.

```text
frontend/.next/verification/
```

이 폴더는 `.next` 아래 빌드/검증 산출물이므로 Git 추적 대상은 아닙니다.

---

## TODO 반영

완료로 체크한 항목:

- mock/live adapter 기반 메시지 순차 렌더링 구조
- mock 기준 `choices` 클릭 시 학생 선택 말풍선 + 다음 코치 응답 누적 렌더링
- TP4 케이스별 선택지 분기 mock 응답
- 수학 케이스 teach-back 텍스트 입력
- TP3 상세 도움 채팅창 전환
- TP5 오답 복습 채팅창 전환
- 학생 선택 드롭다운
- `/` 학생 화면과 `/tp-demo` 내부 검수 화면 분리
- mock/live chat adapter 인터페이스 분리

아직 남긴 항목:

- 실제 T10 `/chat` API 대상 SSE 스트리밍 수신
- `choices` 클릭 시 실제 `POST /chat` 재호출
- T10 `/chat` 연결 후 SSE 스트리밍으로 케이스 1·2 전체 흐름 확인

---

## 다음 작업

T10 백엔드 `/chat` API가 준비되면 `SmartAllCoachApp`에 넘기는 adapter를 `mockChatAdapter`에서 `liveChatAdapter`로 교체합니다.

그 다음 실제 SSE 이벤트 포맷이 현재 `liveChatAdapter`의 파서와 맞는지 확인하고, 필요하면 `parseSseChunk()`만 조정하면 됩니다.
