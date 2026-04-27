# Worklog — feature/T4-5-response-policy

## 작업 배경

프론트 목업과 PRD 검토 과정에서, 세그먼트별 최종 응답 문구는 팀 합의 후 고도화하되 그 전에 공통 응답 골격을 먼저 마련해야 한다는 방향을 정했다.

## 작업 내용

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

## 확인

- `uv run pytest tests/test_response_builders.py` 통과
- 커밋 전 `git diff --check`로 공백 오류 확인

## 다음 작업

- T5~T7 노드에서 공통 helper 사용
