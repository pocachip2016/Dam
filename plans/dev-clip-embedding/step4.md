# Step 2.4: cn-embed-full

> GitHub: 미생성 | Milestone: clip-embedding

## 읽어야 할 파일
- `ingest/clip_worker.py` (Step 2.2)
- `plans/dev-clip-embedding/step3.md` (open_clip 결과 비교 대조)

## 작업
- CN-CLIP 으로 동일 데이터 임베딩 (PK constraint 로 open 결과와 공존):
  ```bash
  MODEL=cn_clip MODEL_NAME=cn-clip-vitb16 BATCH=128 WORKERS=4 \
    THUMB_DIR=/home/ktalpha/Work/Dam/dam_data/thumbnails \
    DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    .venv/bin/python ingest/clip_worker.py
  ```
- 백그라운드 + Monitor (예상 6–10 분, ViT-B/16 가 32 보다 약간 느림)
- 결과 행수·디스크 사용 비교 메모 (DB embeddings 테이블 row 가 약 2배 → 320k)

## Acceptance Criteria
```bash
bash .claude/verify.sh 2.4
```
- `SELECT COUNT(*) FROM embeddings WHERE model_name='cn-clip-vitb16'` ≥ 159,500
- 두 모델 동시 존재 확인: `SELECT model_name, COUNT(*) FROM embeddings GROUP BY model_name` 두 행 모두 ≥ 159,500
- vector 차원 모두 512

## 금지사항
- open_clip 결과를 덮어쓰지 마라. 이유: 모델 비교(Step 2.6) 의 전제. PK=(asset_id, model_name) 으로 공존 가능.
- HNSW 인덱스를 모델별로 분리해서 만들지 마라. 이유: 단일 인덱스로 model_name WHERE 필터링 + cosine 정렬 충분.
