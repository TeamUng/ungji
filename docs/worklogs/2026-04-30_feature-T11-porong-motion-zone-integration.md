# 워크로그: 2026-04-30 T11 뽀롱쌤 Motion 및 섹션 감지 통합

## 기본 정보

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-04-30 |
| 담당 | Codex |
| 작업 범위 | T11 프론트엔드 챗봇 UI |
| 작업 성격 | Motion 기반 뽀롱쌤 오버레이 고도화, 섹션 감지 기능 통합, `/`와 `/tp-demo` 오버레이 단일화 |

---

## 한 줄 요약

> 기존에 분리되어 있던 섹션 감지 챗봇 레이어와 Motion 기반 `PorongOverlay`를 하나로 합치고, 뽀롱쌤이 드래그 위치를 유지하면서 TP 말풍선, 섹션별 제안, dizzy 반응, 채팅창 진입을 모두 같은 오버레이 안에서 처리하도록 정리했다.

---

## 왜 이 작업을 했는가

기존 구현은 두 흐름으로 나뉘어 있었다.

- `/` 홈 화면: `InteractionZone` 기반 섹션 감지 챗봇 레이어
- `/tp-demo`: Motion 기반 `PorongOverlay`와 TP1~TP5 데모

이 구조에서는 한쪽에서 고친 기능이 다른 화면에 반영되지 않았다.
예를 들어 뽀롱쌤을 학습 카드나 오답노트 위에 올렸을 때 섹션별 제안 코멘트가 나와야 하지만, `/tp-demo`에서는 해당 기능이 동작하지 않았다.

따라서 이번 작업의 목표는 다음과 같았다.

- 뽀롱쌤 오버레이를 `PorongOverlay` 하나로 통일한다.
- `/`와 `/tp-demo`가 같은 오버레이 로직을 사용하게 한다.
- 기존 섹션 감지 기능을 버리지 않고 `PorongOverlay` 안으로 흡수한다.
- 드래그 종료 시 캐릭터가 사이드로 밀려나는 문제를 고친다.
- dizzy 반응이 섹션 말풍선에 덮이지 않도록 우선순위를 명확히 한다.

---

## 주요 변경 사항

### 1. Motion 패키지 도입

`motion` 패키지를 추가하고, React 컴포넌트에서는 공식 경로인 `motion/react`를 사용했다.

적용 위치:

- `PorongOverlay.tsx`
- `usePorongDrag.ts`

적용한 목적:

- 드래그 중 손가락을 살짝 늦게 따라오는 느낌
- 탭 반응
- 드래그 중 기울기
- release 시 작은 착지 반응
- `prefers-reduced-motion` 대응

---

### 2. 오른쪽 채팅창 분리

기존 `SmartAllCoachApp.tsx` 내부에 있던 채팅창 렌더링을 `PorongCoachPanel.tsx`로 분리했다.

분리 이유:

- `SmartAllCoachApp`가 화면 흐름과 채팅 UI를 모두 들고 있어 읽기 어려웠다.
- 뽀롱쌤 오버레이와 채팅 패널의 책임을 나누는 편이 이후 유지보수에 유리하다.

---

### 3. 섹션 감지 기능을 `PorongOverlay`로 통합

새 훅을 추가했다.

```text
frontend/src/components/porong/usePorongInteractionZones.ts
```

역할:

- `InteractionZoneProvider`가 있을 때만 zone 문맥을 읽는다.
- 드래그 시작 시 zone rect를 캐싱한다.
- 드래그 중 뽀롱쌤 중심점이 어떤 zone 안에 들어갔는지 계산한다.
- 여러 zone이 겹치면 더 작은 zone을 우선한다.
- active zone이 바뀔 때만 React state를 갱신한다.

이제 `/`와 `/tp-demo` 모두 같은 `PorongOverlay`에서 섹션 제안 말풍선을 보여준다.

---

### 4. `/`와 `/tp-demo` 오버레이 단일화

`/` 홈 화면은 더 이상 구형 `ChatbotOverlayLayer`를 사용하지 않는다.

현재 구조:

```txt
InteractionZoneProvider
  └─ 스마트올 화면
      ├─ InteractionZone 섹션들
      └─ PorongOverlay
```

정리한 구형 파일:

```text
frontend/src/components/chatbot/ChatbotOverlay.tsx
frontend/src/components/chatbot/DraggableChatbot.tsx
```

`frontend/src/components/chatbot/`에는 이제 zone 시스템 파일만 남겼다.

---

### 5. 말풍선 우선순위 정리

말풍선 출처가 여러 개라 우선순위를 명확히 했다.

```txt
1순위: dizzy 메시지
2순위: 섹션별 제안 메시지
3순위: TP1~TP5 기본 말풍선
```

dizzy가 발동하면 2초 동안 다음 문구만 표시된다.

```text
뽀롱~ 어지러워! 천천히 옮겨줘~
```

이 2초 동안은 `오답노트`, `학습시작` 같은 섹션 위에 올라가도 섹션 말풍선이 끼어들지 않는다.

---

### 6. 드래그 종료 위치 유지

초기 계획에는 snap point 이동이 있었지만, 실제 UX에서는 학생이 뽀롱쌤을 특정 섹션 위에 올려두는 것이 중요하다.
그래서 손을 떼면 가장 가까운 사이드로 밀려나는 동작을 제거했다.

현재 동작:

- 드래그 중에는 화면 안전 영역 안에서만 움직인다.
- 손을 떼면 놓은 좌표에 그대로 남는다.
- 화면 밖으로 나갈 때만 clamp 보정한다.
- `/` 홈 화면은 마지막 좌표를 `localStorage`에 저장하고 새로고침 후 복원한다.

추가로 `/tp-demo`의 stage offset 때문에 위치가 조금 어긋나던 문제도 고쳤다.
드래그 시작 시 저장된 논리 좌표가 아니라 실제 렌더링된 DOM 위치를 stage 기준 좌표로 다시 측정한다.

---

## 검증 결과

명령어 검증:

```powershell
cd frontend
npm run lint
npm run build
npx tsc --noEmit
```

결과:

| 검증 | 결과 |
|------|------|
| `npm run lint` | 통과 |
| `npm run build` | 통과 |
| `npx tsc --noEmit` | 통과 |

브라우저 검증:

| 경로 | 확인 내용 | 결과 |
|------|----------|------|
| `/` | 뽀롱쌤 오버레이 표시 | 통과 |
| `/` | `오답노트` zone 위로 드래그 시 섹션 제안 말풍선 표시 | 통과 |
| `/` | 드래그 종료 후 놓은 좌표 유지 | 통과 |
| `/` | 새로고침 후 마지막 좌표 복원 | 통과 |
| `/tp-demo` | 뽀롱쌤 오버레이 표시 | 통과 |
| `/tp-demo` | `오답노트` zone 위로 드래그 시 섹션 제안 말풍선 표시 | 통과 |
| `/tp-demo` | 탭 시 오른쪽 채팅창 열림 | 통과 |
| `/tp-demo` | 빠른 좌우 흔들기 시 dizzy 말풍선 표시 | 통과 |
| `/tp-demo` | dizzy 발동 후 2초 동안 섹션 말풍선 차단 | 통과 |

위치 검증:

| 화면 | 목표 좌표와 실제 위치 오차 |
|------|--------------------------|
| `/` | 약 `0.05px` |
| `/tp-demo` | 약 `0.1px` |

---

## 변경 파일 요약

| 파일/폴더 | 설명 |
|-----------|------|
| `frontend/package.json` | `motion` 의존성 추가 |
| `frontend/src/components/porong/PorongOverlay.tsx` | Motion 기반 오버레이, 말풍선 우선순위, zone 감지 연결 |
| `frontend/src/components/porong/usePorongDrag.ts` | 탭/드래그 판정, 놓은 좌표 유지, DOM 좌표 재측정 |
| `frontend/src/components/porong/useDizzyShake.ts` | 빠른 좌우 흔들기 감지 |
| `frontend/src/components/porong/usePorongInteractionZones.ts` | `InteractionZone` 감지 통합 훅 |
| `frontend/src/components/porong/PorongCoachPanel.tsx` | 오른쪽 채팅창 분리 |
| `frontend/src/components/chatbot/InteractionZone*.tsx` | 섹션 감지 Provider와 zone 등록 구조 |
| `frontend/src/components/chatbot/chatbotSuggestions.ts` | 섹션별 제안 문구 |
| `frontend/src/components/smartall/SmartAllHome.tsx` | 홈 화면에서 `PorongOverlay` 사용 및 좌표 저장/복원 |
| `frontend/src/components/smartall/SmartAllCoachApp.tsx` | `/tp-demo`에 zone 등록 및 `PorongCoachPanel` 연결 |
| `frontend/src/app/globals.css` | 뽀롱쌤, 채팅 패널, zone highlight 스타일 |
| `TODO.md` | 완료 항목 갱신 |

---

## 남은 항목

코드로 처리 가능한 통합 작업은 완료했다.
다음 항목은 별도 자료나 실기기 확인이 필요하다.

- 실제 Galaxy Tab A8 계열 터치 디바이스에서 dizzy cooldown 포함 수동 QA
- 뽀롱쌤 캐릭터와 하단 로고 텍스트가 완전히 분리된 원본 asset 확보
- 실제 포즈별 WebP 프레임 제작
- Rive 또는 Lottie 기반 캐릭터 리깅 도입 여부 검토
