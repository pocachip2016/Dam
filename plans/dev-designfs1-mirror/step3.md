# Step 3.3: ingest-designfs1

> GitHub: 미생성 | Milestone: designfs1-mirror

## 읽어야 할 파일
- `ingest/ingest_local.py` (poc_sample 기준 동작, REALM 하드코딩)
- `docs/phase3-survey.md` (Step 3.2 결과)

## 작업
- `ingest/ingest_local.py` 환경변수화:
  - `REALM` (기본 `poc_sample`) — 다른 realm 지원
  - `SKIP_EXTS` (예: `.psd,.psb`) — 확장자 제외 로직
  - `POC_ROOT` 변수명을 `SCAN_ROOT` 로 일반화 (하위호환 유지)
- DESIGNFS1 ingest 실행:
  ```bash
  SCAN_ROOT=/mnt/designfs1 REALM=designfs1_mirror SKIP_EXTS=.psd,.psb \
    DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    .venv/bin/python ingest/ingest_local.py > dam_data/designfs1_ingest.log 2>&1 &
  ```
- 진행 모니터링 (예상 30–60 분, drvfs/cifs 성능 의존)
- 적재 후 검증:
  - `SELECT COUNT(*) FROM asset_storage WHERE realm='designfs1_mirror'` ≈ Step 3.2 의 ingest 대상 수
  - 확장자 분포 spot check
  - PSD/PSB 가 0건인지 확인

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.3
```
- `asset_storage WHERE realm='designfs1_mirror'` >= Step 3.2 예상 수의 95%
- `assets WHERE primary_ext IN ('.psd','.psb')` ∩ designfs1_mirror = 0
- ingest 로그 `inserted=` 와 DB count 일치

## 금지사항
- 기존 poc_sample realm 데이터 건드리지 마라. 이유: realm 격리 원칙.
- `ON CONFLICT DO UPDATE` 쓰지 마라. `ON CONFLICT DO NOTHING` 만. 이유: 멱등 + 기존 데이터 보존.
- 단일 트랜잭션으로 1.6M INSERT 하지 마라. 이유: WAL 폭주, lock 시간 폭증. 배치 5000 단위.
