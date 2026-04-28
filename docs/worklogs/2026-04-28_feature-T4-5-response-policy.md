# Worklog — feature/T4-5-response-policy

## 작업 배경

프론트 목업과 PRD 검토 과정에서, 세그먼트별 최종 응답 문구는 팀 합의 후 고도화하되 그 전에 공통 응답 골격을 먼저 마련해야 한다는 방향을 정했다.
기존 TODO는 T5~T7 노드별 구현 항목은 있었지만, 여러 팀원이 세그먼트별 문구를 나눠 수정할 때 공통 메시지 타입과 선택지 규칙이 어디에 있는지 명확하지 않았다.

## 왜 필요한가

- PRD는 `text`, `choices`, `image_card`, `hint_card`를 챗봇 UI 허용 요소로 정의한다.
- 프론트는 이 메시지 타입을 기준으로 UI를 렌더링하므로, 백엔드 노드가 제각각 응답을 만들면 연결 비용이 커진다.
- 내부 세그먼트명은 학생 화면에 노출되면 안 되므로, 응답 생성 단계에서 이를 테스트로 막아야 한다.
- 팀원들은 세부 문구를 고도화하되, 메시지 구조와 선택지 id 규칙은 흔들리지 않아야 한다.

## 구현 방법

- 문서와 코드 역할을 분리했다.
  - `docs/SEGMENT_RESPONSE_POLICY.md`: 기획/팀 합의용 정책 문서
  - `app/services/nodes/common.py`: 실제 노드가 사용할 응답 builder와 정책 helper
- 선택지는 `id`와 `label`을 분리했다.
  - `id`: stable snake_case, API/분기용
  - `label`: 학생에게 노출되는 문구
- `ResponsePolicy`를 만들어 `segment + grade_group + current_touchpoint` 기준으로 출력 목표와 메시지 타입을 선택할 수 있게 했다.
- 케이스 1·2 placeholder 응답을 넣어 T5~T7이 아직 없어도 기본 출력 형태를 테스트할 수 있게 했다.
- `tests/test_response_builders.py`로 builder 동작, 내부 세그먼트명 비노출, MVP 케이스 placeholder 구조를 검증했다.

## 변경 내용

- `docs/SEGMENT_RESPONSE_POLICY.md` 신규 작성
  - 세그먼트별 출력 방향
  - TP1~TP5 기본 응답 정책
  - 혼자 먼저 구현 가능한 골격과 팀 합의가 필요한 고도화 영역 분리
- `TODO.md`에 `Phase 1.5 / T4.5` 추가
  - 응답 builder, 선택지 id 규칙, 세그먼트 출력 정책 helper, 테스트 항목 정의
- `docs/ARCHITECTURE_REVIEW.md`에 `nodes/common.py`와 정책 문서 참조 추가
- `docs/STATE_DESIGN.md` 데이터 흐름에 세그먼트 출력 정책 단계를 추가
- `app/services/nodes/common.py` 신규 작성
  - 4개 응답 메시지 타입 builder 구현
  - stable snake_case 선택지 id 검증
  - `segment + grade_group + current_touchpoint` 기반 `ResponsePolicy` 선택 helper 구현
  - 케이스 1·2용 기본 placeholder 응답 구현
- `tests/test_response_builders.py` 신규 작성
  - 메시지 builder 검증
  - 내부 세그먼트명 비노출 검증
  - 케이스 1·2 placeholder 응답 타입 검증

## 주요 변경 파일

- `docs/SEGMENT_RESPONSE_POLICY.md`
  - 세그먼트별 출력 방향과 TP별 기본 정책 정의
  - 혼자 먼저 구현할 공통 골격과 팀 합의 후 고도화할 영역 분리
- `app/services/nodes/common.py`
  - `make_text`, `make_choices`, `make_image_card`, `make_hint_card`, `make_chat_response`
  - stable snake_case 선택지 id 검증
  - `get_response_policy`, `build_placeholder_messages`
- `tests/test_response_builders.py`
  - 메시지 builder schema 검증
  - 내부 세그먼트명 비노출 검증
  - 케이스 1 `못함+불성실`, 케이스 2 `못함+성실` placeholder 검증
- `TODO.md`
  - `Phase 1.5 / T4.5` 추가 및 완료 체크
- `docs/ARCHITECTURE_REVIEW.md`
  - `nodes/common.py`와 Phase 1.5 반영
- `docs/STATE_DESIGN.md`
  - TP 노드 데이터 흐름에 출력 정책 단계 추가

## 확인

- `uv run pytest tests/test_response_builders.py` 통과
- `uv run pytest` 통과
- `git diff --check` 통과

## PR 참고

- PR 대상: `dev`
- 이 PR은 이후 T5~T7 노드가 공통으로 사용할 기반 PR이다.
- 다른 노드 PR보다 먼저 머지하는 것을 권장한다.
- 세그먼트별 최종 문구는 이 PR에서 확정하지 않고, `docs/SEGMENT_RESPONSE_POLICY.md` 기준으로 팀 합의 후 고도화한다.

## 다음 작업

- T5~T7 노드에서 공통 helper 사용
