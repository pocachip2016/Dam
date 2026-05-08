# Step 4.G.3: smoke-test

> GitHub: 미생성 | Milestone: db-init-guard

## 읽어야 할 파일
- `scripts/postgres_entrypoint_guard.sh` (4.G.1)
- 변경된 `docker-compose.yml` (4.G.2)

## 작업
실제 시나리오 시뮬레이션 — 4.G.1·4.G.2 의 효과 검증.

**선행 안전 조치 (필수):**
- `bash scripts/db_backup.sh` — 현재 스키마 백업본 1개 더 생성
- 백업 위치 확인: `ls -la data/backups/` 에 파일 있어야 함

**시나리오 A — 정상 기동 (happy path):**
- `docker compose restart dam_postgres`
- `docker logs dam_postgres --tail 5` 에 정상 startup
- `psql_q "SELECT 1"` == `1`

**시나리오 B — guard 차단 검증 (block path):**
- `docker compose stop dam_postgres`
- `docker run --rm -v $(pwd)/data/pg_data:/data alpine sh -c "rm -rf /data/* /data/.[!.]*"` (pg_data 비우기)
- `docker compose start dam_postgres`
- 1~2초 대기 후 `docker ps -a | grep dam_postgres` 가 `Exited (1)` 상태여야 함
- `docker logs dam_postgres` 에 우리 에러 메시지 출력돼야 함
- **복구**: `docker compose stop dam_postgres` → 백업에서 pg_data 복원
  - 옵션 1: `pg_restore` 가능한 fresh init (시나리오 C 와 결합)
  - 옵션 2: pg_data tar 백업 있으면 그것을 사용 (4.G.3 선행으로 별도 tar 백업 권장)

**시나리오 C — 의도적 fresh init (allow path):**
- pg_data 가 빈 상태에서 `DAM_ALLOW_INIT=yes docker compose up -d dam_postgres`
- 정상 startup, 빈 DB cluster 생성
- `bash scripts/db_backup.sh` 의 가장 최근 dump 로 복원: `pg_restore -U dam -d dam < latest.dump`
- 시나리오 A 다시 실행해 정상 기동 확인

**문서화:**
- `docs/db-recovery.md` 신규 작성 — 위 3 시나리오 + 복구 명령어 정리

## Acceptance Criteria
```bash
bash .claude/verify.sh 4.G.3
```
- 시나리오 A·B·C 각각 수동 수행 후 결과 캡처
- `docs/db-recovery.md` 존재 + 시나리오 3개 명시
- 최종 상태: dam_postgres 정상 기동 + 4.G.3 직전 데이터 복원 완료

## 금지사항
- 백업 없이 시나리오 B 진행 금지. 이유: 복구 불가능한 데이터 유실.
- 시나리오 사이에 컨테이너 RestartPolicy 를 `always` 등으로 변경하여 무한 재시작 루프 방치 금지.
