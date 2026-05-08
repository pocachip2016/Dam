# Dam DB 복구 가이드

> 이 문서는 Step 4.G.3 smoke-test 결과를 바탕으로 작성됐습니다.
> 관련 guard 스크립트: `scripts/postgres_entrypoint_guard.sh`

## 배경

2026-05-07 WSL2 dirty shutdown 으로 `data/pg_data/` 내용이 유실됐고,
`dam_postgres` 컨테이너가 재시작 시 자동으로 빈 cluster 를 새로 초기화(silent initdb)해
161k 에셋·320k 임베딩 데이터가 삭제됐다.

이후 entrypoint guard 를 도입해 빈 pg_data 에서 자동 initdb 를 차단한다.

## Guard 동작

| 상황 | Guard 응답 |
|---|---|
| `PG_VERSION` 존재 | 정상 패스스루 → postgres 기동 |
| `PG_VERSION` 없음 + `DAM_ALLOW_INIT=yes` | 경고 출력 후 패스스루 (fresh init 허용) |
| `PG_VERSION` 없음 + flag 없음 | **⛔ exit 1** — 컨테이너 재시작 루프, 에러 메시지 출력 |

## Scenario A — 정상 기동

```bash
docker compose up -d dam_postgres
docker exec dam_postgres psql -U dam -d dam -tAc "SELECT 1"
# → 1
```

## Scenario B — Guard 차단 (pg_data 비어있을 때)

컨테이너 logs 에 다음 메시지가 출력되며 exit 1:

```
╔══════════════════════════════════════════════════════════════════╗
║  ⛔  dam_postgres STARTUP BLOCKED — DATA DIRECTORY IS EMPTY     ║
...
╚══════════════════════════════════════════════════════════════════╝
```

`docker ps` 에서 `Restarting (1)` 상태로 보임.

**복구:** 아래 Scenario C 진행.

## Scenario C — 의도적 Fresh Init + 백업 복원

pg_data 가 완전히 비어있거나 손상 불복구 시:

```bash
# 1. 컨테이너 중지
docker compose stop dam_postgres

# 2. docker-compose.yml 에서 DAM_ALLOW_INIT 활성화
#    environment: 섹션에서 주석 해제:
#      DAM_ALLOW_INIT: "yes"

# 3. fresh init 허용해 기동
docker compose up -d --force-recreate dam_postgres

# 4. 백업에서 복원 (최신 dump 파일 확인)
LATEST=$(ls -t data/backups/dam_*.dump | head -1)
docker exec -i dam_postgres pg_restore -U dam -d dam --clean --if-exists < "$LATEST"

# 5. DAM_ALLOW_INIT 다시 주석 처리 (docker-compose.yml)
#      # DAM_ALLOW_INIT: "yes"

# 6. 재기동 (guard 정상 패스스루 확인)
docker compose up -d --force-recreate dam_postgres
docker exec dam_postgres psql -U dam -d dam -tAc "SELECT 1"
# → 1
```

## 백업 위치

`data/backups/dam_<YYYYMMDD_HHMMSS>.dump`

- 매주 일요일 03:00 자동 실행 (cron)
- 30일 보존
- 수동 실행: `bash scripts/db_backup.sh`

## WSL2 주의사항

Docker Desktop + WSL2 에서 `mv directory` 로 pg_data 를 교체하면 bind mount 가 inode 캐시를 유지해 guard 가 오작동할 수 있다.
실제 장애(파일 삭제)는 inode 가 유지되므로 guard 가 정상 동작한다.
테스트 시에는 `docker run --rm -v $(pwd)/data/pg_data:/pgdata alpine sh -c "rm -rf /pgdata/* /pgdata/.[!.]*"` 로 inode 를 유지한 채 내용만 삭제할 것.
