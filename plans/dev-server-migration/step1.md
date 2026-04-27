# Step 1: branch-setup

> GitHub: 미생성 | Milestone: server-migration

## 읽어야 할 파일
- `/home/ktalpha/Work/CLAUDE.md` (워크스페이스 규칙 - branch/plans/verify 컨벤션)
- `/home/ktalpha/Work/Dam/CLAUDE.md`

## 작업
- `git checkout -b feature/server-migration` (main 직접 작업 금지)
- `plans/dev-server-migration/index.json` 생성 (project/phase/steps 스키마)
- `plans/dev-server-migration/step1.md ~ step8.md` 각 step 내용 포함
- `.claude/verify.sh` 스켈레톤 — `case "$1" in 1.1) ... ;; --skip) ... ;; esac`

## Acceptance Criteria
```bash
bash .claude/verify.sh 1.1
```
- `git rev-parse --abbrev-ref HEAD` = `feature/server-migration`
- `test -x .claude/verify.sh`
- `test -f plans/dev-server-migration/index.json`

## 금지사항
- main 에 직접 커밋하지 마라. 이유: 워크스페이스 브랜치 컨벤션.
