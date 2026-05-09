-- Phase M.0: content_catalog_mirror + asset_content_link + sync_cursors
-- mediaX ↔ Dam 자산 연결 파이프라인 기반 스키마

-- =============================================================
-- A. mediaX 콘텐츠 미러
-- =============================================================
CREATE TABLE content_catalog_mirror (
    content_id       INT PRIMARY KEY,
    title            TEXT NOT NULL,
    original_title   TEXT,
    content_type     TEXT NOT NULL
                     CHECK (content_type IN ('movie','series','season','episode')),
    production_year  INT,
    status           TEXT NOT NULL,
    mx_updated_at    TIMESTAMPTZ NOT NULL,   -- mediaX 측 updated_at
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ccm_content_type  ON content_catalog_mirror (content_type);
CREATE INDEX idx_ccm_mx_updated_at ON content_catalog_mirror (mx_updated_at);

-- =============================================================
-- B. 자산 ↔ 콘텐츠 매핑 (confidence ≥ 0.85 기준)
-- =============================================================
CREATE TABLE asset_content_link (
    asset_id    BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    content_id  INT    NOT NULL REFERENCES content_catalog_mirror(content_id) ON DELETE CASCADE,
    confidence  REAL,
    method      TEXT NOT NULL
                CHECK (method IN ('clip_similarity','ocr_text','manual','web_search')),
    status      TEXT NOT NULL DEFAULT 'candidate'
                CHECK (status IN ('candidate','confirmed','rejected')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, content_id)
);

CREATE INDEX idx_acl_content ON asset_content_link (content_id);
CREATE INDEX idx_acl_status  ON asset_content_link (status);
CREATE INDEX idx_acl_method  ON asset_content_link (method);

-- updated_at 자동 갱신 (trigger_set_updated_at은 001_init.sql에서 정의됨)
CREATE TRIGGER set_acl_updated_at
    BEFORE UPDATE ON asset_content_link
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================
-- C. 폴링 커서 (M.1 워커가 읽고 씀)
-- =============================================================
CREATE TABLE sync_cursors (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO sync_cursors (key, value) VALUES ('content_mirror_next_ts', '0');
