# Step 4.G.2: compose-integration

> GitHub: 미생성 | Milestone: db-init-guard

## 읽어야 할 파일
- `docker-compose.yml`
- `scripts/postgres_entrypoint_guard.sh` (4.G.1 산출물)

## 작업
- `docker-compose.yml` `dam_postgres` 서비스에:
  - `entrypoint: ["/usr/local/bin/dam_init_guard.sh"]`
  - `command: ["postgres"]` (기존 묵시적 CMD 명시화)
  - `volumes` 에 추가: `./scripts/postgres_entrypoint_guard.sh:/usr/local/bin/dam_init_guard.sh:ro`
  - 기존 mount 들(`./data/pg_data`, `./db/migrations`) 유지
- 컨테이너 재시작 (현재 데이터 보호를 위해 **반드시 백업 선행**):
  1. `bash scripts/db_backup.sh`
  2. `docker compose up -d dam_postgres` (이미 띄워진 컨테이너에 신규 entrypoint 반영 위해 `--force-recreate` 옵션 사용)
  3. `docker logs dam_postgres --tail 20` 로 정상 startup 확인

## Acceptance Criteria
```bash
bash .claude/verify.sh 4.G.2
```
- `docker compose config -q` 통과
- `docker exec dam_postgres ls -la /usr/local/bin/dam_init_guard.sh` 가 executable 로 보임
- `docker exec dam_postgres ps -ef | grep -c "postgres"` ≥ 1 (정상 기동)
- DB 응답: `psql_q "SELECT 1"` == `1`

## 금지사항
- 백업 없이 컨테이너 down/up 금지. 이유: 4.G.2 자체는 mount 추가일 뿐이지만, 만약 entrypoint 가 잘못 작성되면 startup 실패하므로 안전망 필수.
- `docker compose down -v` 사용 금지. 이유: 볼륨 삭제 위험, 우리 목표와 정반대.
