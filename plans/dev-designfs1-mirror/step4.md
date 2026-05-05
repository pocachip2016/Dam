# Step 3.4: thumbnail-full

> GitHub: 미생성 | Milestone: designfs1-mirror

## 읽어야 할 파일
- `ingest/thumbnail_worker.py` (REALM='poc_sample' 하드코딩, IMAGE_EXTS 정의)
- Step 3.3 결과 (designfs1_mirror 적재 완료)

## 작업
- `thumbnail_worker.py` 환경변수화:
  - `REALM` env (기본 `poc_sample`)
- 썸네일 디렉토리 결정: `dam_data/thumbnails_designfs1/<id//1000>/<id>.jpg`
  - poc_sample 과 디렉토리 분리해서 충돌 방지
- 실행:
  ```bash
  REALM=designfs1_mirror \
    THUMB_DIR=/home/ktalpha/Work/Dam/dam_data/thumbnails_designfs1 \
    WORKERS=8 \
    DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    .venv/bin/python ingest/thumbnail_worker.py > dam_data/designfs1_thumb.log 2>&1 &
  ```
- 예상 시간: 1.2M 이미지 × 6ms = ~2 시간 (CIFS read latency 의존)
- 진행 모니터링: 1만 단위 로그
- 완료 후 검증:
  - `SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id WHERE s.realm='designfs1_mirror' AND a.thumbnail_path IS NOT NULL` >= image 자산 수의 95%
  - 디스크 사용량 spot check (~30–50 GB 예상)

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.4
```
- designfs1_mirror image 자산의 thumbnail_path 채움률 >= 95%
- `dam_data/thumbnails_designfs1/` 디스크 사용량 > 10 GB

## 금지사항
- poc_sample 의 `dam_data/thumbnails/` 에 섞어 쓰지 마라. 이유: realm 격리, 디렉토리 분리.
- 동시에 hash_worker 또는 ingest 실행하지 마라. 이유: CIFS read 경합 + 디스크 I/O 폭주.
- `WORKERS=16` 이상 올리지 마라. 이유: CIFS 동시 핸들 한계, 오히려 느려짐.
