# Step 3.6: hash-dedup

> GitHub: 미생성 | Milestone: designfs1-mirror

## 읽어야 할 파일
- `ingest/hash_worker.py` (UNC↔로컬 변환, ThreadPool, 4MB 청크 SHA-256)
- `db/migrations/001_init.sql` (`asset_edges` `relation='duplicate_of'`)

## 작업
- `hash_worker.py` 환경변수 검토:
  - `DAM_LOCAL_PREFIX` → `/mnt/designfs1`
  - `DAM_UNC_PREFIX` → DESIGNFS1 의 UNC (필요시 코드 분기)
  - 또는 realm 필터 추가 (`DAM_REALM=designfs1_mirror`)
- 실행:
  ```bash
  DAM_REALM=designfs1_mirror DAM_LOCAL_PREFIX=/mnt/designfs1 \
    DAM_WORKERS=8 DAM_BATCH_SIZE=500 \
    DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    .venv/bin/python ingest/hash_worker.py > dam_data/designfs1_hash.log 2>&1 &
  ```
- 예상 시간: 1.66M 파일 × CIFS read 평균 시간. 실제 1.48 TB 처리 = 수 시간 (병목: CIFS 네트워크)
- 완료 후:
  - `SELECT COUNT(*) FROM assets WHERE sha256 IS NOT NULL AND sha256 <> 'ERROR'` 95%+
  - 중복 그룹 검출 → `asset_edges (relation='duplicate_of')` 생성
- 통계 보고:
  - 중복 그룹 수, 절약 가능 용량
  - poc_sample ↔ designfs1_mirror 간 중복 (sha256 매칭)
  - `docs/phase3-dedup-report.md` 작성

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.6
```
- `assets WHERE sha256 IS NOT NULL` (designfs1_mirror) >= 95%
- `asset_edges WHERE relation='duplicate_of'` > 0 (중복이 1쌍 이상 있다는 가정)
- `docs/phase3-dedup-report.md` 존재 + 절약 용량 명시

## 금지사항
- 중복 자동 삭제 금지. 이유: 불문율 (PRD §불문율). 플래그만, 사람이 판단.
- WORKERS 를 16+ 로 올리지 마라. 이유: CIFS 동시 read 한계.
- sha256='ERROR' 자산을 retry 무한 시도하지 마라. 이유: 깨진 파일·권한 문제, 한 번 마킹 후 스킵.
