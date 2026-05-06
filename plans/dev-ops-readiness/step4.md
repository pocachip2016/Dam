# Step 4.4: backup

> GitHub: 미생성 | Milestone: ops-readiness

## 읽어야 할 파일
- `docker-compose.dev.yml` (postgres volume 정의)
- `dam_data/` 구조 (썸네일/임베딩/모델)

## 작업
- DB 덤프 스크립트 `scripts/backup_db.sh`:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  STAMP=$(date +%Y%m%d_%H%M)
  pg_dump --format=custom -Fc -h localhost -p 15432 -U dam dam \
    > /backup/dam_${STAMP}.dump
  find /backup -name 'dam_*.dump' -mtime +7 -delete
  ```
- 썸네일 디렉토리 rsync `scripts/backup_thumbs.sh`:
  - 로컬 `dam_data/thumbnails/` → 외장 백업 영역
  - `rsync -a --delete` (소스가 truth — 백업이 소스 따라감)
  - 임베딩은 백업 X (DB 에 있고 모델/썸네일에서 재생성 가능)
  - 모델 (`dam_data/models/`) 은 1회만 백업 (변경 빈도 낮음)
- cron `deploy/crontab.template`:
  ```
  0 3 * * *  bash /opt/dam/scripts/backup_db.sh     >> /var/log/dam/backup_db.log 2>&1
  0 4 * * 0  bash /opt/dam/scripts/backup_thumbs.sh >> /var/log/dam/backup_thumbs.log 2>&1
  ```
- 복원 리허설 (별도 DB 인스턴스, docker container):
  - 최신 dump 로드 → row count 비교 → 검색 1건 PASS
  - 절차 문서화 `docs/restore-procedure.md`:
    - 단계별 명령
    - 예상 시간
    - rollback 시나리오
    - 데이터 손실 윈도 (24h dump 주기 → 최대 24h 손실)

## Acceptance Criteria
```bash
bash .claude/verify.sh 4.4
```
- backup_db.sh 1회 실행 → `/backup/dam_*.dump` 생성, 모의 8일 전 파일 retention 동작
- 복원 리허설: 별도 DB 에 dump 로드 → `SELECT COUNT(*) FROM assets` 일치
- `docs/restore-procedure.md` 존재 + 최소 4 섹션 (백업/복원/롤백/손실윈도)

## 금지사항
- `pg_dump -Fp` (plain SQL) 사용 금지. 이유: 161k+ 자산은 plain 이 느리고 트랜잭션 단위 복원 불가.
- rsync `--delete` 를 백업디스크 → 소스 방향으로 돌리지 마라. 이유: 소스 데이터 삭제 위험.
- 백업 디스크에 secret 동거 저장 금지. 이유: 분실 시 노출.
- 복원 리허설 빠뜨리지 마라. 이유: 검증 안 된 백업은 백업이 아님.
