# Step 4.6: wrap

> GitHub: 미생성 | Milestone: ops-readiness

## 읽어야 할 파일
- `TODO.md`, `CLAUDE.md`, `docs/PRD.md`
- `plans/dev-ops-readiness/index.json`
- `docs/deployment.md`, `docs/restore-procedure.md`

## 작업
- `docs/PRD.md` Phase 4 줄: `대기` → `✅ 완료` 갱신
- `TODO.md` — Done 갱신, Phase 5 (실데이터 이관) 인프라 협의 결과에 따라 Now/Next 결정
- `CLAUDE.md` Active Work — Phase 4 (ops-readiness) 완료, Phase 5 검토 시작 표시
- `plans/dev-ops-readiness/index.json` 모든 step `"completed"` + summary 한 줄
- `docs/operations.md` 작성:
  - 일일 체크리스트 (헬스, 백업 결과, 워커 진행률)
  - 주간 체크리스트 (디스크 사용량, 에러 추이, 복원 dry-run)
  - 장애 대응 매뉴얼 (DB 죽음 / API 죽음 / 워커 hang)
- 커밋 분할 (scaffold / auth / monitoring / backup / deployment / docs)
- `--no-ff` 머지 → main → 브랜치 정리

## Acceptance Criteria
```bash
bash .claude/verify.sh --skip "wrap-up: docs + merge"
```
- `docs/PRD.md` Phase 4 행 `✅ 완료`
- `docs/operations.md` 존재 + 3 섹션
- `git log --oneline main` 에 머지 커밋
- 로컬 브랜치 `feature/ops-readiness` 삭제됨

## 금지사항
- 사용자 명시 승인 없이 push / 머지 / 브랜치 삭제 금지.
- prod 환경 변수 git 커밋 금지.
