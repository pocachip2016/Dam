# Step 4.5: deployment

> GitHub: 미생성 | Milestone: ops-readiness

## 읽어야 할 파일
- `deploy/Caddyfile.template`, `deploy/.env.prod.template` (Step 4.1 스켈레톤)
- `deploy/systemd/*.service` (Step 4.1 스켈레톤)

## 작업
- `docker-compose.prod.yml` 완성:
  - `postgres`: named volume, `restart: unless-stopped`, healthcheck (`pg_isready`)
  - `redis`: Phase 5 캐시 대비
  - `dam-api`: uvicorn `--workers 4`, healthcheck `GET /health`
  - `caddy`: reverse proxy, env-driven basic-auth, optional TLS (local CA 또는 Let's Encrypt staging)
  - 모든 서비스 `restart: unless-stopped`
  - 외부 노출 포트 = caddy 만, 나머지 internal network only
  - 기본 bind = `127.0.0.1` (외부 노출은 사용자 명시 결정 시점에 변경)
- systemd unit 등록:
  - `deploy/systemd/dam.service` — `ExecStart=docker compose -f docker-compose.prod.yml up`
  - `deploy/systemd/dam-workers@.service` — instance: `dam-workers@metadata`, `dam-workers@ocr`, …
  - `WorkingDirectory=/opt/dam`, `EnvironmentFile=/etc/dam/env.prod` (chmod 600, root)
- `/opt/dam` 배포 디렉토리 + `dam` system user 생성 (별도 sudo 스크립트 `scripts/install_system.sh`)
- `/health` endpoint 활용 (Step 4.3 에서 추가됨)
- 배포 가이드 `docs/deployment.md`:
  - 1회 setup (user/dir/secret/systemctl enable) 절차
  - 업데이트 절차 (git pull → migration → restart)
  - 롤백 절차 (이전 image tag pin)

## Acceptance Criteria
```bash
bash .claude/verify.sh 4.5
```
- `docker compose -f docker-compose.prod.yml config` PASS (yaml 검증)
- `systemctl --user start dam.service` 또는 system 단위 dry-run PASS
- `curl 127.0.0.1:8080/health` 200 (auth 우회)
- 외부 IP 직접 호출 시 reset/blocked 확인 (127.0.0.1 bind 검증)
- `docs/deployment.md` 존재 + setup/update/rollback 3 섹션

## 금지사항
- prod 환경에서 uvicorn `--reload` 금지. 이유: dev 전용, 메모리 폭증.
- 0.0.0.0 바인드 / 외부 노출 디폴트 금지. 이유: 사용자 명시 결정 필요.
- secret 을 image / git 에 하드코딩 금지. 이유: 노출 + image 공유 위험.
- `/health` 에 DB write 또는 무거운 쿼리 포함 금지. 이유: liveness 전용.
