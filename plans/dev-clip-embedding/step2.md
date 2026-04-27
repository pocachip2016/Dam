# Step 2.2: worker-impl

> GitHub: 미생성 | Milestone: clip-embedding

## 읽어야 할 파일
- `ingest/thumbnail_worker.py` (배치 패턴, 멀티프로세스 패턴 참고)
- `ingest/ingest_local.py` (DB 연결·COPY 패턴)
- `db/migrations/002_embeddings.sql` (vector(512) 스키마)
- `api/search.py` (`/similar/{id}` 가 가정하는 model_name)

## 작업
- `ingest/clip_worker.py` 신규 작성
  - **환경변수**:
    - `MODEL` ∈ {`open_clip`, `cn_clip`} (default `open_clip`)
    - `MODEL_NAME` (DB 저장값, default 모델별 — `clip-vit-b32` / `cn-clip-vitb16`)
    - `BATCH` (default 128), `WORKERS` (DataLoader CPU, default 4)
    - `THUMB_DIR` (default `~/Work/Dam/dam_data/thumbnails`)
    - `DAM_DSN`, `MODEL_CACHE_DIR` (`~/Work/Dam/dam_data/models`)
  - **흐름**:
    1. 모델 dispatch (`MODEL=open_clip` → open_clip ViT-B/32 laion2b / `MODEL=cn_clip` → cn_clip ViT-B/16)
    2. 멱등 쿼리: `LEFT JOIN embeddings WHERE e.asset_id IS NULL AND e.model_name=%s AND a.thumbnail_path IS NOT NULL`
    3. PyTorch DataLoader (워커 N, `__getitem__` = PIL.open + preprocess)
    4. GPU 배치 인코딩 → `.cpu().numpy().astype('float32')`
    5. psycopg COPY 또는 `executemany` INSERT (`ON CONFLICT (asset_id, model_name) DO NOTHING`)
    6. 100 배치마다 진행 로그 + 멱등 재시작 검증
  - **에러 정책**:
    - PIL/IO 에러 → log.warning + skip + 카운터
    - GPU OOM → 자동 batch /=2 후 재시도 1회
- `ingest/clip_worker.py --help` (argparse 또는 click 없이 env 만, README 주석으로 충분)

## Acceptance Criteria
```bash
bash .claude/verify.sh 2.2
```
- `python -c "from ingest.clip_worker import main"` 성공
- 1k smoke run: `LIMIT=1000 MODEL=open_clip .venv/bin/python ingest/clip_worker.py` → embeddings ≥ 1000
- DB: `SELECT COUNT(*) FROM embeddings WHERE model_name='clip-vit-b32'` ≥ 1000

## 금지사항
- `model_name` 을 하드코딩하지 마라. 이유: open_clip 과 cn_clip 둘 다 같은 워커로 처리해야 함.
- 원본 (`physical_path`) 을 읽지 마라. 이유: drvfs read latency 누적, 16만 × 평균 363 KB 비효율. 썸네일 (`assets.thumbnail_path`) 사용.
- 단일 INSERT 루프로 16만 건 넣지 마라. 이유: TPS 50× 손실. COPY 또는 batch executemany.
- DataLoader workers 가 GPU 컨텍스트를 fork 하지 않도록 주의 (multiprocessing context = `spawn`).
