# Step 3: env-prepare

> GitHub: #4 | Milestone: server-migration

## 읽어야 할 파일
- `docker-compose.yml` (pocachip 경로 2곳 확인)
- `docs/migration-status.md` (이전 PC 볼륨 경로 이슈 참조)
- `plans/dev-server-migration/index.json`

## 작업
- `/home/ktalpha/dam_data/{pg_data,redis_data}/` 생성 (ext4, WSL2 내부)
- `docker-compose.yml` 볼륨 경로 치환: `/home/pocachip/dam_data/` → `/home/ktalpha/dam_data/` (2곳)
- `requirements.txt` 신규 — `psycopg[binary]`, `fastapi`, `uvicorn`, `Pillow`
- `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

## Acceptance Criteria
```bash
bash .claude/verify.sh 1.3
```
- `docker compose config -q` 통과
- `.venv/bin/python -c "import fastapi, psycopg, PIL, uvicorn"` 통과
- `test -d /home/ktalpha/dam_data/pg_data`

## 금지사항
- NTFS 경로(`/mnt/c`, `/mnt/d`)를 PG volume 으로 쓰지 마라. 이유: chmod 미지원 → PostgreSQL 기동 실패 (이전 PC 와 동일한 이슈).
- venv 를 git 에 추가하지 마라. 이유: .gitignore 에 `.venv/` 등록됨.
