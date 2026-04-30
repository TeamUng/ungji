# 스마트올 AI 학습코치 프론트엔드

T11에서 구현한 Next.js 기반 태블릿 화면 목업입니다.

이 프론트엔드는 별도 챗봇 앱이 아니라, 웅진 스마트올의 `오늘의 학습` 화면과 학습 화면 위에 **AI 코치 캐릭터 레이어**가 얹히는 구조를 확인하기 위한 구현입니다.

## 실행

```bash
npm install
npm run dev
```

브라우저에서 아래 주소를 열면 됩니다.

```text
http://127.0.0.1:3000
```

학생에게 보이는 자연 흐름은 `/`에서 확인합니다.
TP별 내부 검수 컨트롤은 아래 주소에서 확인합니다.

```text
http://127.0.0.1:3000/tp-demo
```

## 확인 포인트

- `/tp-demo`의 mock 학생 드롭다운으로 `1~2학년 국어`, `5~6학년 수학` 케이스를 전환합니다.
- `/tp-demo`의 `홈 추천`, `학습`, `도움`, `완료`, `이탈`, `마무리` 버튼으로 TP1~TP5 흐름을 확인합니다.
- 오른쪽 아래 AI 코치 캐릭터는 드래그할 수 있습니다.
- AI 코치 캐릭터를 누르면 TP4 학습 도움용 오른쪽 채팅 패널이 열립니다.
- 선택지를 누르면 학생 선택 말풍선이 쌓이고, mock adapter가 케이스·TP·선택지별 응답을 순차 렌더링합니다.
- 수학 `식을 어떻게 세울지 모르겠어요` 흐름에서는 teach-back 입력창이 나타납니다.

## 구조

```text
src/app/page.tsx
  첫 화면 진입점입니다.

src/app/tp-demo/page.tsx
  TP별 내부 검수 컨트롤이 있는 시연 화면입니다.

src/components/smartall/SmartAllCoachApp.tsx
  스마트올 화면, AI 코치, 채팅 패널, 상태 전환을 연결하는 핵심 컴포넌트입니다.

src/lib/mock-chat.ts
  실제 /chat API가 준비되기 전까지 사용하는 mock adapter입니다.

src/lib/live-chat.ts
  T10 이후 실제 /chat 또는 SSE 응답을 연결할 live adapter입니다.

src/types/chat.ts
  백엔드 app/schemas/chat.py와 맞춘 프론트 메시지 타입입니다.
```

## 검증 명령

```bash
npm run lint
npm run build
```
