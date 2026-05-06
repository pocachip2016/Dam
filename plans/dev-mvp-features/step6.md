# Step 3.6: ocr-pipeline

> GitHub: 미생성 | Milestone: mvp-features

## 읽어야 할 파일
- `ingest/clip_worker.py` (GPU batch + progress logging 패턴)
- Step 3.2 결과 (`role_hint='poster'` 자산을 우선 처리 가능)

## 작업
- 마이그레이션 `db/migrations/005_ocr.sql`:
  ```sql
  ALTER TABLE assets
    ADD COLUMN ocr_text     TEXT,
    ADD COLUMN ocr_lang     TEXT,         -- 'ko'|'en'|'mixed'|'none'
    ADD COLUMN ocr_done_at  TIMESTAMPTZ,
    ADD COLUMN ocr_tsv      tsvector
      GENERATED ALWAYS AS (to_tsvector('simple', coalesce(ocr_text, ''))) STORED;
  CREATE INDEX idx_assets_ocr_tsv ON assets USING GIN (ocr_tsv);
  ```
- 새 워커 `ingest/ocr_worker.py`:
  - PaddleOCR (`use_gpu=True, lang='korean'`) 1차, 실패/예외 시 `pytesseract` fallback
  - 입력 = `thumbnail_path` (이미 생성된 썸네일, 원본 read 비용 회피)
  - WHERE 조건:
    ```sql
    mime LIKE 'image/%'
      AND thumbnail_path IS NOT NULL
      AND ocr_done_at IS NULL
    ORDER BY ('poster' = ANY(role_hint) OR 'banner' = ANY(role_hint)) DESC, id
    ```
  - 결과: `ocr_text` (공백 압축), `ocr_lang` (langdetect), `ocr_done_at = now()`
  - 빈 결과/실패도 `ocr_done_at` 기록 → 재처리 방지 (재시도는 `ocr_done_at = NULL` 명시 reset)
- Smoke 1000건 (poster 우선) → 한글 정확도 spot check → 전체 161k 야간 배치
- 실행:
  ```bash
  DAM_DSN=... DAM_BATCH=64 SMOKE=1000 \
    .venv/bin/python ingest/ocr_worker.py > dam_data/poc_ocr_smoke.log 2>&1 &
  # smoke 검수 후
  DAM_DSN=... DAM_BATCH=64 \
    .venv/bin/python ingest/ocr_worker.py > dam_data/poc_ocr_full.log 2>&1 &
  ```
- 예상 시간: 161k × ~150ms (RTX 4060) = ~7 시간 (야간 배치 OK)
- `/search_text` 통합 (`api/search.py`):
  - `q` 시 OCR text 매칭도 결과에 포함 (CLIP 시맨틱 + OCR 텍스트 가산점, 또는 union)
  - 응답에 `ocr_snippet` 필드 (`ts_headline`)
  - 디버깅 옵션 `?text_search=ocr_only`

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.6
```
- `assets WHERE ocr_done_at IS NOT NULL` (image 자산) ≥ 80%
- `assets WHERE length(ocr_text) > 5` ≥ 40% (포스터/배너 비중 한계)
- 한글 샘플 5개 (알려진 작품명 / 카피) 검색 → 결과 ≥ 1
- `EXPLAIN /search_text?q=...` 에서 `idx_assets_ocr_tsv` 사용 확인

## 금지사항
- 원본 NAS 파일에 직접 OCR 돌리지 마라. 이유: PSD/대용량 read 비용. 썸네일 사용.
- PaddleOCR 디폴트 파라미터로 prod 배포 금지. 이유: 한글 짧은 카피 누락. smoke 결과 기반 1회 튜닝 (`det_db_box_thresh` 등).
- `ocr_text=''` 와 NULL 동일 취급 금지 — NULL=미처리 / ''=처리했으나 무텍스트. 이유: 재처리 트리거 구분.
- 재시도 시 모든 row reset 금지. 이유: 7시간 배치 재시작.
