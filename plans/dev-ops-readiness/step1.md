# Step 4.1: branch-and-scaffold

> GitHub: 미생성 | Milestone: ops-readiness

## 읽어야 할 파일
- `CLAUDE.md` (Branch convention)
- `docker-compose.yml` (현재 dev stack)
- Phase 3 머지 결과 (main HEAD 상태)

## 작업
- main 에서 `feature/ops-readiness` 브랜치 생성 (Phase 3 머지 후)
- `deploy/` 디렉토리 + 스켈레톤 파일:
  - `deploy/systemd/dam.service` (compose wrap)
  - `deploy/systemd/dam-workers@.service` (instance 화)
  - `deploy/.env.prod.template` (환경변수 키만, 값은 빈 placeholder)
  - `deploy/Caddyfile.template`
  - `deploy/crontab.template`
- 기존 `docker-compose.yml` → `docker-compose.dev.yml` 으로 git mv (history 보존)
- `docker-compose.prod.yml` 신규 (Step 4.5 에서 채워짐) — placeholder 헤더만

## Acceptance Criteria
```bash
bash .claude/verify.sh 4.1
```
- `git rev-parse --abbrev-ref HEAD` == `feature/ops-readiness`
- `deploy/` 디렉토리 + 5 template 존재
- `docker-compose.dev.yml` 존재, `docker-compose.yml` 없음
- `docker-compose.prod.yml` 존재 (내용 placeholder OK)

## 금지사항
- main 에서 직접 작업 금지. 이유: branch convention.
- secret 값을 template 에 하드코딩 금지. 이유: git 노출.
- docker-compose.yml 단순 삭제 금지 — git mv 로 history 보존.
