# 워크로그: 2026-04-29 T11 뽀롱쌤 Asset System 및 오버레이 적용

## 기본 정보

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-04-29 |
| 담당 | Codex |
| 작업 범위 | T11 프론트엔드 챗봇 UI |
| 작업 성격 | 뽀롱쌤 캐릭터 asset system 구축, 드래그 가능한 AI 학습코치 오버레이 구현 |
| 기준 문서 | `docs/PRD.md`, `docs/FRONTEND_USER_FLOW.md`, 뽀롱쌤 페르소나 PR #25 논의 내용 |

---

## 한 줄 요약

> 기존 CSS 얼굴형 AI 코치를 실제 뽀롱쌤 투명 이미지 기반의 드래그 가능한 캐릭터 오버레이로 교체하고, TP1~TP5 흐름에 맞춰 상태별 모션과 말풍선 연동 구조를 만들었다.

---

## 왜 이 작업을 했는가

기존 프론트엔드에는 AI 코치가 CSS로 만든 임시 얼굴 형태로 들어가 있었다.
하지만 실제 서비스 방향에서는 뽀롱쌤이 단순한 챗봇 버튼이 아니라, 스마트올 학습 화면 위에 떠 있는 학습 파트너 역할을 해야 한다.

그래서 이번 작업의 목표는 다음과 같았다.

- 뽀롱쌤을 하나의 대표 캐릭터로 유지한다.
- 학년별로 캐릭터를 바꾸지 않고, 상태와 말투만 다르게 표현한다.
- 제공받은 투명 PNG 원본 품질을 유지한다.
- 캐릭터 본체는 WebP/PNG, UI 장식은 SVG로 관리한다.
- 학습 화면 위에서 탭과 드래그가 가능한 오버레이로 구현한다.
- TP1~TP5 유저 플로우에 맞춰 말풍선, 채팅창, 상태 모션을 연결한다.

---

## 제공받은 원본 asset

사용자가 제공한 투명 PNG를 기준 asset으로 사용했다.

```text
C:/Users/sesac/Downloads/뽀롱쌤-Photoroom.png
```

확인한 원본 특성:

- 크기: 1254 x 1254
- 투명도: alpha 채널 있음
- 형식: PNG
- 구성: 뽀롱쌤 캐릭터와 하단 로고 텍스트가 함께 포함된 이미지

주의할 점:

- 현재 원본은 캐릭터와 로고가 완전히 분리된 레이어 파일이 아니다.
- 따라서 1차 구현에서는 원본을 WebP로 변환해 상태별 파일을 구성하고, 실제 표정 변화는 CSS 모션과 장식 효과로 표현했다.
- 향후 진짜 애니메이션 수준으로 가려면 눈, 입, 팔, 몸통, 소품을 분리한 asset이 추가로 필요하다.

---

## asset 폴더 구축

다음 구조로 뽀롱쌤 전용 asset 폴더를 만들었다.

```text
frontend/public/assets/porong/
  brand/
  mascot/
  ui/
  motion/
```

### brand asset

| 파일 | 설명 |
|------|------|
| `frontend/public/assets/porong/brand/porong-logo-full-original.png` | 제공받은 투명 PNG 원본 보관본 |
| `frontend/public/assets/porong/brand/porong-logo-full.webp` | UI 사용을 위한 WebP 변환본 |

### mascot asset

| 파일 | 설명 |
|------|------|
| `porong-overlay-idle.webp` | 기본 대기 상태 |
| `porong-overlay-welcome.webp` | 첫 진입, 환영 상태 |
| `porong-overlay-thinking.webp` | 답변 생성, 고민 상태 |
| `porong-overlay-speaking.webp` | 말하는 상태 |
| `porong-overlay-hint.webp` | 힌트 제공 상태 |
| `porong-overlay-cheer.webp` | 정답, 완료, 칭찬 상태 |
| `porong-overlay-comfort.webp` | 오답, 이탈, 복습 제안 상태 |
| `porong-overlay-confused.webp` | 이해 실패, 헷갈림 상태 |
| `porong-overlay-touched.webp` | 터치 반응 상태 |
| `porong-overlay-dragging.webp` | 드래그 중 상태 |
| `porong-overlay-hanging.webp` | 매달림 표현용 상태 |
| `porong-overlay-snapping.webp` | 놓은 뒤 착지 상태 |
| `porong-overlay-edge.webp` | 화면 가장자리 대기 상태 |
| `porong-head.webp` | 작은 아바타/헤더 사용용 머리 중심 asset |

현재 위 mascot 파일들은 대부분 같은 원본 crop을 공유한다.
즉, 파일 구조는 상태별로 준비했지만 실제 포즈 차이는 아직 이미지 프레임이 아니라 CSS 모션으로 표현한다.

### ui asset

| 파일 | 설명 |
|------|------|
| `frontend/public/assets/porong/ui/star.svg` | 칭찬, 완료, 보상 효과 |
| `frontend/public/assets/porong/ui/sparkle.svg` | 반짝임, 생각 중, 힌트 효과 |
| `frontend/public/assets/porong/ui/speech-tail.svg` | 말풍선 꼬리 |
| `frontend/public/assets/porong/ui/wand.svg` | 힌트/마법봉 아이콘 |

---

## 추가한 프론트엔드 구조

뽀롱쌤 오버레이를 별도 컴포넌트 영역으로 분리했다.

```text
frontend/src/components/porong/
  porongTypes.ts
  porongAssets.ts
  PorongMascot.tsx
  PorongSpeechBubble.tsx
  PorongOverlay.tsx
  usePorongDrag.ts
  usePorongSnap.ts
```

### `porongTypes.ts`

뽀롱쌤 상태값과 터치포인트 타입을 정의했다.

주요 상태:

- `idle`
- `welcome`
- `thinking`
- `speaking`
- `hint`
- `cheer`
- `comfort`
- `confused`
- `touched`
- `dragging`
- `hanging`
- `snapping`
- `edge`

이렇게 타입을 먼저 만든 이유는 프론트엔드에서 캐릭터를 다음처럼 상태 기반으로 제어하기 위해서다.

```tsx
<PorongOverlay state="thinking" />
```

상태값을 문자열로 통일해두면 나중에 이미지, Lottie, Rive, CSS 중 어떤 방식으로 바뀌어도 화면 로직은 크게 흔들리지 않는다.

### `porongAssets.ts`

상태값과 실제 asset 경로를 매핑했다.

예를 들면:

```ts
thinking -> /assets/porong/mascot/porong-overlay-thinking.webp
cheer -> /assets/porong/mascot/porong-overlay-cheer.webp
```

이 파일이 있으면 컴포넌트 내부에서 이미지 경로를 직접 하드코딩하지 않아도 된다.
나중에 asset을 교체할 때도 이 매핑 파일만 바꾸면 된다.

### `PorongMascot.tsx`

실제 뽀롱쌤 이미지를 렌더링하는 컴포넌트다.

역할:

- Next.js `Image`로 WebP asset을 표시한다.
- 현재 상태를 `data-state`로 CSS에 전달한다.
- 반짝임, 별, glow 같은 장식 요소를 함께 렌더링한다.

### `PorongSpeechBubble.tsx`

뽀롱쌤 옆에 붙는 말풍선 컴포넌트다.

역할:

- TP1~TP5에 맞는 짧은 메시지를 보여준다.
- CTA 버튼을 렌더링한다.
- 채팅창을 열기 전 가벼운 추천/칭찬/위로 메시지를 표현한다.

### `PorongOverlay.tsx`

뽀롱쌤 오버레이의 중심 컴포넌트다.

역할:

- 뽀롱쌤 이미지와 말풍선을 함께 배치한다.
- 탭하면 채팅창을 열도록 `onTap`을 호출한다.
- 드래그 이벤트를 `usePorongDrag`에 연결한다.
- `isPressed`, `isDragging`, `isSnapping` 상태에 따라 시각 상태를 바꾼다.

상태 우선순위:

```text
드래그 중이면 dragging
누르는 중이면 touched
스냅 중이면 snapping
그 외에는 외부에서 전달받은 state 사용
```

### `usePorongDrag.ts`

탭과 드래그를 구분하는 핵심 훅이다.

구현 기준:

- `pointerdown`, `pointermove`, `pointerup` 기반
- 마우스와 터치 입력 모두 대응
- 이동 거리 8px 미만은 탭으로 처리
- 이동 거리 8px 이상은 드래그로 처리
- 드래그 종료 시 가까운 snap point로 이동
- pointer 이벤트가 제대로 잡히지 않는 환경을 위해 click fallback도 제공

이 구조를 사용한 이유:

- 초등학생 사용자는 손가락 움직임이 정확하지 않을 수 있다.
- 아주 작은 손떨림까지 드래그로 처리하면 채팅창 열기가 불편해진다.
- 그래서 8px 기준선을 두어 탭과 드래그를 안정적으로 나눴다.

### `usePorongSnap.ts`

드래그가 끝났을 때 뽀롱쌤이 어디에 붙을지 계산하는 훅이다.

지원 snap point:

- `bottom-right`
- `middle-right`
- `bottom-left`
- `top-right`
- `middle-left`
- `top-left`

MVP에서 주로 사용하는 위치:

- `bottom-right`
- `middle-right`
- `bottom-left`

추가로 처리한 내용:

- 화면 밖으로 나가지 않도록 위치를 보정한다.
- 채팅창이 열려 있을 때 오른쪽 패널과 겹치지 않도록 보정한다.
- 세로형 태블릿 화면에서도 실제 보이는 stage 너비를 기준으로 위치를 계산한다.

---

## 기존 화면에 연결한 내용

### `SmartAllCoachApp.tsx`

기존 CSS 얼굴형 코치 컴포넌트를 제거하고 `PorongOverlay`로 교체했다.

TP별 상태 연결:

| 상황 | 뽀롱쌤 상태 |
|------|-------------|
| 답변 생성 중 | `thinking` |
| 채팅창 열림 + 도움 단계 | `hint` |
| 채팅창 열림 | `speaking` |
| 홈/오늘 학습 추천 | `welcome` |
| 학습 완료 | `cheer` |
| 이탈 시도 | `comfort` |
| 오늘 학습 종료, 오답 복습 있음 | `comfort` |
| 기본 | `idle` |

이렇게 연결한 이유:

- 뽀롱쌤이 단순히 화면에 떠 있는 장식이 아니라 학습 상황에 반응하는 캐릭터로 느껴져야 한다.
- PRD와 유저 플로우에서 정의한 TP1~TP5가 캐릭터 상태와 바로 이어져야 한다.

### `ChatbotOverlay.tsx`

`/`에서 기존 `DraggableChatbot` 대신 `PorongOverlay`를 사용하도록 바꿨다.

동작:

- 뽀롱쌤을 탭하면 작은 말풍선이 표시된다.
- 다시 탭하면 말풍선이 닫힌다.
- 드래그로 위치 이동이 가능하다.

---

## 구현된 상호작용

### 탭

뽀롱쌤을 짧게 누르면 채팅창 또는 말풍선이 열린다.

```text
pointerdown
pointerup
이동 거리 8px 미만
=> tap 처리
```

### 드래그

뽀롱쌤을 8px 이상 움직이면 드래그 모드로 전환된다.

```text
pointerdown
pointermove
이동 거리 8px 이상
=> dragging 처리
```

드래그 중에는 다음 시각 효과가 적용된다.

- 살짝 확대
- 이동 방향에 따른 기울기
- 손가락에 매달린 듯한 느낌
- 말풍선은 방해되지 않도록 숨김

### 스냅

손을 떼면 가장 가까운 안전 위치로 이동한다.

```text
pointerup
=> 가장 가까운 snap point 계산
=> snapping 상태
=> 착지 bounce
=> idle 상태 복귀
```

---

## 구현된 CSS 모션

`frontend/src/app/globals.css`에 뽀롱쌤 전용 스타일과 keyframes를 추가했다.

상태별 모션:

| 상태 | 표현 |
|------|------|
| `idle` | 아주 약한 둥실둥실 움직임 |
| `welcome` | 첫 진입 환영 느낌의 둥실거림 |
| `touched` | 눌렸을 때 살짝 커지고 위로 반응 |
| `dragging` | 손가락에 매달려 흔들리는 느낌 |
| `snapping` | 놓은 뒤 통통 착지 |
| `thinking` | 고민 중인 듯한 기울임과 반짝임 |
| `hint` | 힌트 제공을 강조하는 반짝임 |
| `speaking` | 말하는 듯한 작은 움직임 |
| `cheer` | 정답/완료 시 팝업 점프와 별 효과 |
| `comfort` | 오답/이탈 상황의 부드러운 흔들림 |
| `confused` | 헷갈리는 듯한 갸웃 움직임 |

접근성 대응:

- `prefers-reduced-motion: reduce`가 켜진 환경에서는 애니메이션을 줄이도록 처리했다.

---

## 현재 구현의 한계

이번 구현은 실제 제품 적용을 위한 1차 MVP다.

현재 방식:

```text
한 장의 뽀롱쌤 이미지
+ WebP asset system
+ CSS transform
+ SVG 장식 효과
+ pointer 기반 드래그
```

아직 아닌 것:

```text
눈만 따로 깜빡임
입만 따로 움직임
팔/마법봉이 별도로 움직임
몸통이 실제로 늘어남
프레임별 포즈가 바뀜
Rive/Lottie 기반 리깅
```

즉, 현재는 “이미지 전체가 살아 움직이는 느낌”은 구현했지만,
“캐릭터 부위가 각각 실제로 움직이는 수준”은 아직 아니다.

---

## 실제 애니메이션 수준으로 가기 위한 다음 작업

다음 단계에서는 asset 제작과 프론트엔드 구현을 함께 진행해야 한다.

### 1차 고도화

우선 상태별 포즈 이미지를 추가한다.

필요 asset:

- `porong-hanging-left.webp`
- `porong-hanging-right.webp`
- `porong-speaking-1.webp`
- `porong-speaking-2.webp`
- `porong-blink.webp`
- `porong-cheer-1.webp`
- `porong-cheer-2.webp`
- `porong-comfort.webp`
- `porong-snap.webp`

목표:

- 드래그 중 왼쪽/오른쪽 매달림 포즈를 실제 이미지로 표현한다.
- speaking 상태에서 입 모양이 2프레임으로 바뀌게 한다.
- idle 상태에서 눈 깜빡임을 보여준다.
- cheer 상태에서 점프/별 효과가 더 분명하게 보이게 한다.

### 2차 고도화

캐릭터를 부품별로 분리한다.

필요 asset:

- 몸통
- 눈 뜬 상태
- 눈 감은 상태
- 기본 입
- 말하는 입 1
- 말하는 입 2
- 마법봉 든 팔
- 책 든 팔
- 안경
- 학사모
- 리본
- 그림자
- 별/반짝임

목표:

- 눈, 입, 팔, 몸통을 따로 움직인다.
- 손가락 방향에 따라 팔과 몸이 자연스럽게 따라오게 한다.
- 말하는 중에는 입만 움직이게 한다.

### 3차 고도화

Rive 또는 Lottie 기반 캐릭터 리깅을 검토한다.

검토 조건:

- 디자이너가 레이어 분리 원본을 제공할 수 있는가
- 보급형 태블릿에서 성능 문제가 없는가
- 프론트엔드에서 상태 제어 API를 안정적으로 유지할 수 있는가

---

## 검증 결과

명령어 검증:

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

화면 검증:

| 경로 | 결과 |
|------|------|
| `/` | HTTP 200, 뽀롱쌤 오버레이 표시 확인 |
| `/tp-demo` | HTTP 200, TP 흐름과 채팅창 연결 확인 |

뷰포트 검증:

| 크기 | 결과 |
|------|------|
| 1280x800 | 오버레이가 화면 안에 표시됨 |
| 800x1280 | 세로형 화면에서도 오버레이가 화면 밖으로 나가지 않도록 보정됨 |

추가 확인:

- `/tp-demo`에서 뽀롱쌤 탭 후 채팅창 열림 확인
- 선택지 버튼 표시 확인
- 채팅창과 캐릭터가 겹치지 않도록 위치 보정 확인
- Chrome DevTools Protocol 기반 자동 측정에서 오버레이가 viewport 안에 들어오는 것 확인

주의:

- synthetic pointer drag 자동 검증은 React pointer handler를 완전히 재현하지 못해 직접적인 자동 드래그 이동 확인은 제한이 있었다.
- 실제 구현은 `pointerdown`, `pointermove`, `pointerup` 기반이므로 브라우저에서 마우스/터치로 수동 확인이 필요하다.

---

## 변경 파일 요약

| 파일/폴더 | 설명 |
|-----------|------|
| `frontend/public/assets/porong/brand/` | 원본 및 브랜드 WebP asset |
| `frontend/public/assets/porong/mascot/` | 뽀롱쌤 상태별 mascot WebP asset |
| `frontend/public/assets/porong/ui/` | 별, 반짝임, 말풍선 꼬리, 마법봉 SVG |
| `frontend/src/components/porong/porongTypes.ts` | 뽀롱쌤 상태/터치포인트 타입 |
| `frontend/src/components/porong/porongAssets.ts` | 상태별 asset 경로 매핑 |
| `frontend/src/components/porong/PorongMascot.tsx` | 뽀롱쌤 이미지 렌더링 |
| `frontend/src/components/porong/PorongSpeechBubble.tsx` | 말풍선 렌더링 |
| `frontend/src/components/porong/PorongOverlay.tsx` | 전체 오버레이 제어 |
| `frontend/src/components/porong/usePorongDrag.ts` | 탭/드래그 상호작용 |
| `frontend/src/components/porong/usePorongSnap.ts` | safe area 및 snap 위치 계산 |
| `frontend/src/components/smartall/SmartAllCoachApp.tsx` | 기존 CSS 코치를 뽀롱쌤 오버레이로 교체 |
| `frontend/src/components/chatbot/ChatbotOverlay.tsx` | 홈/스마트올 화면의 코치 오버레이 교체 |
| `frontend/src/app/globals.css` | 뽀롱쌤 스타일과 상태별 애니메이션 추가 |

---

## 현재 상태

현재 뽀롱쌤 작업은 다음 단계까지 완료된 상태다.

```text
asset 폴더 구축: 완료
투명 PNG 원본 보관: 완료
WebP 변환 asset 구성: 완료
SVG UI 장식 asset 구성: 완료
PorongOverlay 컴포넌트 구현: 완료
탭/드래그 구분: 완료
safe snap 위치 계산: 완료
TP1~TP5 상태 연결: 완료
CSS 기반 캐릭터 모션: 완료
lint/build 검증: 완료
실제 프레임/부품 애니메이션: 다음 단계
```

---

## 다음 작업 제안

다음 작업은 “진짜 움직이는 뽀롱쌤”을 위한 asset 고도화다.

우선순위는 다음 순서가 좋다.

1. `hanging-left/right` 포즈 이미지를 제작한다.
2. `speaking-1/2` 입 모양 프레임을 제작한다.
3. `blink` 눈 깜빡임 프레임을 제작한다.
4. `cheer-1/2` 칭찬 포즈를 제작한다.
5. 이후 눈/입/팔/몸통 분리형 asset으로 확장한다.

이 순서가 좋은 이유는 단순하다.
지금 컴포넌트 구조는 이미 상태 기반으로 준비되어 있으므로, 상태별 이미지만 더 정교해지면 프론트엔드 로직을 크게 바꾸지 않고 퀄리티를 빠르게 올릴 수 있다.
