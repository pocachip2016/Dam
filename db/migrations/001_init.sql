-- 001_init.sql
-- Phase 1 초기 스키마: Dual Store + Unified Graph 기반
--
-- 설계 원칙
--   1. 파일이 아니라 "자산(asset)"이 1급 시민. 한 자산은 여러 realm에 물리 존재 가능.
--   2. 관계(버전/분해/구성/파생/중복/유사)는 모두 asset_edges 그래프.
--   3. 분류 체계(프로젝트/연도/캠페인/컴포넌트)는 asset_tags 다축 태그.
--      → "이상적 폴더 구조"는 태그 기반 가상 뷰로 동적 생성.
--   4. 원본 NAS는 불변(source realm). AI 생성물은 DAM CAS(dam_cas realm)에 저장.
--   5. 이 파일은 Phase 1 범위(메타 전량 적재 + 해시 타깃)만 다룬다.
--      embeddings/thumbnails 등 Phase 2+ 확장은 별도 마이그레이션으로 추가.

-- =============================================================
-- 0. 확장
-- =============================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector, Phase 2부터 사용

-- =============================================================
-- 1. 스캔 감사 로그
-- =============================================================
CREATE TABLE scan_runs (
    id           BIGSERIAL PRIMARY KEY,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    realm        TEXT NOT NULL,
    source_root  TEXT NOT NULL,       -- 예: '\\designfs.ktalpha.com\DESIGNFS\디자인파트'
    total_files  BIGINT,
    total_bytes  BIGINT,
    notes        JSONB
);

-- =============================================================
-- 2. 자산 (asset) - 물리 경로와 독립된 정체성
-- =============================================================
CREATE TABLE assets (
    id            BIGSERIAL PRIMARY KEY,
    asset_type    TEXT NOT NULL
                  CHECK (asset_type IN ('source', 'derivative', 'ai_generated', 'composition')),
    sha256        TEXT,                -- 64 hex (소문자), 해시 워커가 채움
    filename      TEXT,                -- 표준 파일명 (basename)
    primary_ext   TEXT,                -- 소문자 확장자 ('.psd' '.jpg'), 점 포함
    size_bytes    BIGINT,
    mtime         TIMESTAMPTZ,
    width         INT,
    height        INT,
    duration_ms   INT,
    ai_metadata   JSONB,                -- AI 생성 메타(caption/objects/colors 등) Phase 3+
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN assets.asset_type IS
    'source: NAS 원본 | derivative: 썸네일/OCR/분해물 | ai_generated: AI 생성 변주 | composition: 가상 합성체';
COMMENT ON COLUMN assets.sha256 IS
    'Phase 1 적재 시점엔 NULL. hash_worker.py가 Phase 1.4에서 채움.';

-- =============================================================
-- 3. 물리 저장 위치 (asset_storage) - 1:N
-- =============================================================
CREATE TABLE asset_storage (
    id               BIGSERIAL PRIMARY KEY,
    asset_id         BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    realm            TEXT NOT NULL
                     CHECK (realm IN (
                         'designfs',               -- 원본 NAS (인증된 원본)
                         'designfs1_mirror',       -- Phase 3 미러 (원본 복제)
                         'designfs1_derivatives',  -- Phase 3+ 서버측 파생물
                         'dam_cas',                -- 로컬 DAM content-addressed store
                         'poc_sample'              -- Phase 2 로컬 샘플
                     )),
    physical_path    TEXT NOT NULL,
    top_folder       TEXT,              -- source realm: 인벤토리 파서가 채움 (쿼리 성능용 비정규화)
    sub_folder       TEXT,
    is_authoritative BOOLEAN NOT NULL DEFAULT true,
    discovered_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    scan_run_id      BIGINT REFERENCES scan_runs(id),
    UNIQUE (realm, physical_path)
);

-- =============================================================
-- 4. 그래프 관계 (asset_edges)
-- =============================================================
CREATE TABLE asset_edges (
    parent_id   BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    child_id    BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    relation    TEXT NOT NULL
                CHECK (relation IN (
                    'decomposed_into',  -- PSD → 레이어들
                    'composed_of',      -- composition → 구성 요소들
                    'variant_of',       -- 사이즈/언어/톤 변주
                    'version_of',       -- v2 → v1
                    'derived_from',     -- 썸네일/OCR/프록시
                    'duplicate_of',     -- 동일 sha256
                    'similar_to',       -- CLIP 유사도
                    'used_in'           -- composed_of 역방향 편의
                )),
    role        TEXT,                   -- composed_of 시 'logo' 'background' 'text' 등
    confidence  REAL,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (parent_id, child_id, relation),
    CHECK (parent_id <> child_id)
);

-- =============================================================
-- 5. 다축 태그 (asset_tags) - 가상 뷰의 재료
-- =============================================================
CREATE TABLE asset_tags (
    asset_id    BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    namespace   TEXT NOT NULL,          -- 'project' | 'year' | 'designer' | 'component_type' | 'campaign' ...
    value       TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'path_inference'
                CHECK (source IN ('path_inference', 'exif', 'ai', 'human')),
    confidence  REAL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, namespace, value)
);

-- =============================================================
-- 6. 저장된 가상 뷰 정의 (views)
-- =============================================================
-- JSONB 쿼리 스펙 예:
--   {"filters": [{"ns": "project", "eq": "NEXT_UI"},
--                {"ns": "year", "eq": "2025"}],
--    "relations": [],
--    "order_by": "mtime DESC"}
CREATE TABLE views (
    name        TEXT PRIMARY KEY,
    description TEXT,
    query       JSONB NOT NULL,
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================
-- 7. 인덱스
-- =============================================================
CREATE INDEX idx_assets_sha256         ON assets (sha256) WHERE sha256 IS NOT NULL;
CREATE INDEX idx_assets_ext            ON assets (primary_ext);
CREATE INDEX idx_assets_type           ON assets (asset_type);
CREATE INDEX idx_assets_size           ON assets (size_bytes);
CREATE INDEX idx_assets_mtime          ON assets (mtime) WHERE mtime IS NOT NULL;
CREATE INDEX idx_assets_filename_trgm  ON assets USING gin (filename gin_trgm_ops);
CREATE INDEX idx_assets_ai_metadata    ON assets USING gin (ai_metadata);

CREATE INDEX idx_storage_asset         ON asset_storage (asset_id);
CREATE INDEX idx_storage_realm_top     ON asset_storage (realm, top_folder);
CREATE INDEX idx_storage_top           ON asset_storage (top_folder) WHERE top_folder IS NOT NULL;
CREATE INDEX idx_storage_path_trgm     ON asset_storage USING gin (physical_path gin_trgm_ops);

CREATE INDEX idx_edges_parent          ON asset_edges (parent_id, relation);
CREATE INDEX idx_edges_child           ON asset_edges (child_id, relation);

CREATE INDEX idx_tags_ns_value         ON asset_tags (namespace, value);
CREATE INDEX idx_tags_value            ON asset_tags (value);
CREATE INDEX idx_tags_asset_ns         ON asset_tags (asset_id, namespace);

-- =============================================================
-- 8. 트리거 - updated_at 자동 갱신
-- =============================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_assets_updated_at
    BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================
-- 9. 편의 뷰 - 파일 중심 쿼리용 (Phase 1 호환)
-- =============================================================
CREATE VIEW v_source_files AS
SELECT
    a.id               AS asset_id,
    s.id               AS storage_id,
    s.physical_path    AS path,
    s.realm,
    s.top_folder,
    s.sub_folder,
    a.filename,
    a.primary_ext      AS extension,
    a.size_bytes,
    a.sha256,
    a.mtime,
    s.discovered_at    AS scanned_at
FROM assets a
JOIN asset_storage s ON s.asset_id = a.id
WHERE a.asset_type = 'source'
  AND s.is_authoritative;

COMMENT ON VIEW v_source_files IS
    'Phase 1에서 인벤토리 전량 적재된 source realm의 파일 중심 뷰. 기존 검증/통계 쿼리 재사용용.';

-- =============================================================
-- 10. 검증 쿼리 예시 (주석)
-- =============================================================
-- -- 확장자별 집계
-- SELECT primary_ext, COUNT(*), SUM(size_bytes)/1e9 AS gb
-- FROM assets WHERE asset_type = 'source'
-- GROUP BY primary_ext ORDER BY gb DESC LIMIT 30;
--
-- -- 탑레벨별 집계
-- SELECT s.top_folder, COUNT(*) AS files, SUM(a.size_bytes)/1e9 AS gb
-- FROM asset_storage s JOIN assets a ON a.id = s.asset_id
-- WHERE s.realm = 'designfs' GROUP BY s.top_folder ORDER BY gb DESC;
--
-- -- 완전 중복 그룹 (해시 워커 실행 후)
-- SELECT sha256, COUNT(*) AS copies, SUM(size_bytes)/1e9 AS wasted_gb
-- FROM assets WHERE sha256 IS NOT NULL
-- GROUP BY sha256 HAVING COUNT(*) > 1
-- ORDER BY wasted_gb DESC LIMIT 100;
--
-- -- 파일명 trigram 검색
-- SELECT * FROM v_source_files
-- WHERE filename ILIKE '%NEXT_UI%' LIMIT 50;

-- =============================================================
-- 11. Phase 2+ 확장 포인트 (구현 시 002_, 003_ 마이그레이션으로 추가)
-- =============================================================
-- 002_embeddings.sql:
--   CREATE TABLE embeddings (
--     asset_id BIGINT REFERENCES assets(id),
--     model_name TEXT,
--     vector vector(512),
--     created_at TIMESTAMPTZ,
--     PRIMARY KEY (asset_id, model_name)
--   );
--   CREATE INDEX ON embeddings USING hnsw (vector vector_cosine_ops)
--     WITH (m=16, ef_construction=64);
--
-- 003_thumbnails.sql:
--   -- 썸네일은 assets(type='derivative') + asset_edges('derived_from')로 모델링
--   -- 여기선 조회 성능용 인덱스만 추가
--   CREATE INDEX idx_edges_deriv_thumb ON asset_edges (parent_id)
--     WHERE relation = 'derived_from';
--
-- 004_ocr.sql:
--   CREATE TABLE ocr_results (asset_id, text, lang, created_at);
--   CREATE INDEX ON ocr_results USING gin (text gin_trgm_ops);
