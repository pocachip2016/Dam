# Step 3.2: metadata-and-tokens

> GitHub: 미생성 | Milestone: mvp-features

## 읽어야 할 파일
- `db/migrations/001_init.sql` (`assets` 테이블 구조)
- `ingest/scan_worker.py` (path/filename 처리 패턴 참고)
- `docs/ARCHITECTURE.md` (메타 흐름)

## 작업
- 마이그레이션 `db/migrations/003_metadata.sql`:
  ```sql
  ALTER TABLE assets
    ADD COLUMN metadata_json   JSONB,
    ADD COLUMN folder_tokens   TEXT[],
    ADD COLUMN filename_tokens TEXT[],
    ADD COLUMN year_hint       INT,
    ADD COLUMN role_hint       TEXT[];
  CREATE INDEX idx_assets_folder_tokens   ON assets USING GIN (folder_tokens);
  CREATE INDEX idx_assets_filename_tokens ON assets USING GIN (filename_tokens);
  CREATE INDEX idx_assets_year_hint       ON assets (year_hint);
  CREATE INDEX idx_assets_role_hint       ON assets USING GIN (role_hint);
  ```
- 키워드 사전 분리: `ingest/role_keywords.py`
  - 한/영 → role 매핑 dict (poster, banner, keyart, thumbnail, background, logo, detail)
  - 향후 확장 위해 별도 파일
- 새 워커 `ingest/metadata_worker.py`:
  - 시그니처: `process(asset_id, physical_path) -> dict`
  - EXIF/IPTC/XMP 추출 — pyexiftool batch mode (`-stay_open True`) 권장
  - 경로 → folder_tokens (구분자 `/` `\`, 빈 토큰 제거)
  - basename → filename_tokens (lowercase, `[_\-\s\.]+` split, 한글/영문/숫자 경계 분리, len≥2 필터)
  - 정규식 `(19|20)\d{2}` 매칭 → year_hint (가장 큰 값)
  - role_keywords 사전 매칭 → role_hint[]
  - UPDATE assets SET ...
- 실행:
  ```bash
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    DAM_REALM=poc_sample DAM_BATCH=500 DAM_WORKERS=4 \
    .venv/bin/python ingest/metadata_worker.py > dam_data/poc_metadata.log 2>&1 &
  ```
- 예상 시간: 161k × ~50ms (image 만 EXIF) = ~2 시간
- 검증:
  ```sql
  SELECT
    COUNT(*) FILTER (WHERE folder_tokens IS NOT NULL)         AS path_done,
    COUNT(*) FILTER (WHERE metadata_json IS NOT NULL)         AS exif_done,
    COUNT(*) FILTER (WHERE year_hint IS NOT NULL)             AS year_done,
    COUNT(*) FILTER (WHERE array_length(role_hint,1) > 0)     AS role_done
  FROM assets WHERE id IN (SELECT asset_id FROM asset_storage WHERE realm='poc_sample');
  ```

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.2
```
- `folder_tokens IS NOT NULL` 채움률 ≥ 95% (모든 자산에 path 가 있음)
- image 자산에서 `metadata_json IS NOT NULL` ≥ 90%
- `year_hint` ≥ 30%
- `role_hint` (1+ 매칭) ≥ 20%
- GIN 인덱스 4개 존재 (`pg_indexes` 확인)

## 금지사항
- exiftool subprocess 1회 spawn-per-file 금지. 이유: 161k × fork 비용. batch mode 또는 Python lib.
- folder_tokens 에 빈 문자열만 포함되게 두지 마라. 이유: GIN 노이즈.
- metadata_json 에 binary preview / large blob 저장 금지. 이유: DB 크기 폭증.
- 기존 컬럼 (filename, primary_ext, mtime, size_bytes) 변경 금지. 이유: 다른 워커가 의존.
