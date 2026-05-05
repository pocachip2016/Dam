# Step 3.5: embed-full

> GitHub: 미생성 | Milestone: designfs1-mirror

## 읽어야 할 파일
- `ingest/clip_worker.py` (realm-agnostic, thumbnail_path 기반)
- `docs/ADR.md` ADR-007 (clip-vit-b32 기본 채택)

## 작업
- ADR-007 에 따라 `clip-vit-b32` 만 실행 (cn_clip 은 poc_sample 비교용으로만 보존, 1.2M 추가 임베딩 시간 비용 vs 효용 낮음)
- 실행:
  ```bash
  MODEL=open_clip MODEL_NAME=clip-vit-b32 BATCH=128 WORKERS=4 \
    THUMB_DIR=/home/ktalpha/Work/Dam/dam_data/thumbnails_designfs1 \
    DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    .venv/bin/python ingest/clip_worker.py > dam_data/designfs1_embed.log 2>&1 &
  ```
- 예상 시간: 1.2M × 1/360s = ~55 분 (RTX 4060 기준)
- 진행 모니터링: 100 배치마다 로그
- 완료 후 검증:
  - `embeddings WHERE model_name='clip-vit-b32'` 증가량 = ~1.2M (poc_sample 160k + designfs1 1.2M = ~1.36M 총합)
  - 무작위 자산 5개 `/similar/{id}` 200 + 결과 ≥ 5

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.5
```
- designfs1_mirror image 자산의 임베딩 채움률 >= 95% (ok+err mask 기준 cf. clip_worker.py)
- 단일 모델 (`clip-vit-b32`) 만 추가 — `embeddings WHERE model_name='cn-clip-vitb16'` 증가 0

## 금지사항
- cn_clip 도 동시에 돌리지 마라. 이유: GPU VRAM + 시간 비용. ADR-007 결정 적용.
- 새 HNSW 인덱스 만들지 마라. 이유: 단일 인덱스로 충분 (ADR-007), 다음 step 에서 ef_search 만 튜닝.
- 임베딩 도중 thumbnail_worker 추가 실행 금지. 이유: 디스크 I/O + VRAM 경합.
