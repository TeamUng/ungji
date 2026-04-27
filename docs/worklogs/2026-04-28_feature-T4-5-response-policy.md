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

## 확인

- 문서 변경 중심 작업으로 애플리케이션 테스트는 실행하지 않음
- 커밋 전 `git diff --check`로 공백 오류 확인 예정

## 다음 작업

- `app/services/nodes/common.py` 응답 builder 구현
- `tests/test_response_builders.py` 작성
- T5~T7 노드에서 공통 helper 사용
