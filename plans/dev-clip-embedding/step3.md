# Step 2.3: open-embed-full

> GitHub: 미생성 | Milestone: clip-embedding

## 읽어야 할 파일
- `ingest/clip_worker.py` (Step 2.2 결과)
- `plans/dev-clip-embedding/index.json`

## 작업
- 전량 임베딩 실행:
  ```bash
  MODEL=open_clip MODEL_NAME=clip-vit-b32 BATCH=128 WORKERS=4 \
    THUMB_DIR=/home/ktalpha/Work/Dam/dam_data/thumbnails \
    DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    .venv/bin/python ingest/clip_worker.py
  ```
- 백그라운드 + Monitor 진척 (예상 4–8 분)
- 완료 후 DB 스폿 체크:
  - 행 수 (160k 근접)
  - vector 차원 정합 (512)
  - 임의 자산 5개 `/similar/{id}` 200 + top-5 시각 검수
- HNSW EXPLAIN: `EXPLAIN (ANALYZE, BUFFERS) SELECT ... ORDER BY vector <=> %s LIMIT 20` → `Index Scan using idx_embeddings_hnsw`

## Acceptance Criteria
```bash
bash .claude/verify.sh 2.3
```
- `SELECT COUNT(*) FROM embeddings WHERE model_name='clip-vit-b32'` ≥ 159,500 (35 PIL err 허용)
- 임의 자산 1개 `/similar/{id}?model=clip-vit-b32` HTTP 200 + results ≥ 5
- HNSW 인덱스가 사용됨을 EXPLAIN 으로 확인

## 금지사항
- 동시에 다른 워커(thumbnail/ingest) 실행하지 마라. 이유: drvfs read 경합 + GPU 메모리 단일 점유 가정.
- API 가 켜진 채로 INSERT 16만건 진행 시 응답 latency 영향 가능 — 가능하면 API 일시 중지.
