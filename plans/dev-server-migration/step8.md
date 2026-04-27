# Step 8: wrap

> GitHub: #9 | Milestone: server-migration

## 읽어야 할 파일
- `TODO.md`, `CLAUDE.md` (현재 상태)
- `plans/dev-server-migration/index.json` (모든 step summary 확인)
- `docs/migration-status.md` (이관 후 검증 결과 확인)

## 작업
- `TODO.md` — Done 섹션에 이관 항목 추가, Now 비우기
- `CLAUDE.md` Active Work 갱신 — Branch: main, 최근: 서버이관 완료 (2026-04-27)
- `plans/dev-server-migration/index.json` — 모든 step `"status": "completed"` + `"summary"` 한 줄, `"completed_at"` 기록
- 머지 (사용자 승인 후):
  ```bash
  git checkout main
  git merge --no-ff feature/server-migration -m "feat: server migration to ktalpha PC + harness alignment"
  git push origin main
  git branch -d feature/server-migration
  ```

## Acceptance Criteria
```bash
bash .claude/verify.sh --skip "wrap-up: docs + merge + push"
```

## 금지사항
- 사용자 명시 승인 없이 push / 브랜치 삭제하지 마라. 이유: 워크스페이스 규칙 — 파괴적 git 조작은 명시 승인 필요.
- index.json 의 summary 를 비우지 마라. 이유: 다음 세션 컨텍스트 복원의 핵심.
