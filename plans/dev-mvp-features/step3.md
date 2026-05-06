# Step 3.3: hash-dedup

> GitHub: 미생성 | Milestone: mvp-features

## 읽어야 할 파일
- `ingest/hash_worker.py` (현재 UNC↔로컬 변환 로직)
- `db/migrations/001_init.sql` (`asset_edges` `relation='duplicate_of'`)

## 작업
- `hash_worker.py` 환경변수 검토 (필요 시 코드 분기 추가):
  - `DAM_REALM=poc_sample`
  - `DAM_LOCAL_PREFIX=/mnt/d/Work/dam_poc_sample` (UNC 변환 안 함, 로컬 경로 직접 사용)
  - 기존 코드가 UNC 변환 강제하면 realm 분기 추가
- 실행:
  ```bash
  DAM_REALM=poc_sample DAM_LOCAL_PREFIX=/mnt/d/Work/dam_poc_sample \
    DAM_WORKERS=8 DAM_BATCH_SIZE=500 \
    DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    .venv/bin/python ingest/hash_worker.py > dam_data/poc_hash.log 2>&1 &
  ```
- 예상 시간: 161k × ~30ms (로컬 SSD) = ~80 분
- 완료 후:
  - `assets WHERE sha256 IS NOT NULL AND sha256 <> 'ERROR'` ≥ 95%
  - sha256 GROUP BY 로 중복 그룹 검출 → `asset_edges (relation='duplicate_of', src_asset_id, dst_asset_id)` 생성
- 통계 보고 `docs/dedup-report.md`:
  - 중복 그룹 수, 절약 가능 용량 (`SUM(size_bytes) - MAX(size_bytes) per group`)
  - TOP 10 중복 그룹 (가장 절약량 큰 순)
  - poc_sample 내부 self-duplication 분포

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.3
```
- `assets WHERE sha256 IS NOT NULL` (poc_sample) ≥ 95%
- `asset_edges WHERE relation='duplicate_of'` > 0
- `docs/dedup-report.md` 존재 + 절약 용량 명시

## 금지사항
- 중복 자동 삭제 금지. 이유: PRD §불문율, 플래그만 사람이 판단.
- WORKERS 16+ 금지. 이유: 로컬 SSD I/O 한계.
- `sha256='ERROR'` 자산 무한 retry 금지. 이유: 깨진 파일·권한 문제는 한 번 마킹 후 스킵.
