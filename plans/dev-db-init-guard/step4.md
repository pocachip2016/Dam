# Step 4.G.4: wrap

> GitHub: 미생성 | Milestone: db-init-guard

## 읽어야 할 파일
- `TODO.md`, `CLAUDE.md`
- `plans/dev-db-init-guard/index.json`

## 작업
- `TODO.md` Done 최상단에 `Step 4.G.* db-init-guard 완료 (YYYY-MM-DD)` 추가, Now 비움
- `CLAUDE.md` Active Work 갱신:
  - "Phase 4 운영 준비 (auth / monitoring / backup / deployment)" 줄 옆에 `db-init-guard ✅ 완료` 또는 별도 줄로 첫 번째 진척 명시
- `plans/dev-db-init-guard/index.json` 모든 step `"completed"` + summary 한 줄
- 커밋 1개 (분할 불필요): `chore(ops): db-init-guard — postgres entrypoint guard + smoke test docs`
- 사용자 승인 후 push

## Acceptance Criteria
```bash
bash .claude/verify.sh --skip "wrap-up: docs commit + push 완료"
```
- TODO/CLAUDE 갱신 확인
- index.json 4 step 모두 completed
- `git log --oneline` 최상단에 chore(ops) 커밋

## 금지사항
- main 으로 직접 머지 금지 — 일단 `feature/db-init-guard` 브랜치에서 작업, wrap 시점에 사용자 승인 받아 머지.
- 사용자 승인 없이 push / 머지 금지.
