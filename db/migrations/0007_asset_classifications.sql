-- M.2: asset_classifications + asset_content_link method 확장 + mapper cursor

CREATE TABLE asset_classifications (
    asset_id        BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    class           TEXT NOT NULL CHECK (class IN (
                       'content','promotion','seasonal','pricing','branding',
                       'ui_service','composition','draft','unclassified')),
    sub_class       TEXT,
    confidence      REAL,
    method          TEXT NOT NULL CHECK (method IN (
                       'folder_pattern','filename_keyword','role_hint',
                       'tag','manual','rule')),
    matched_signal  TEXT,
    status          TEXT NOT NULL DEFAULT 'candidate'
                    CHECK (status IN ('candidate','confirmed','rejected')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, class)
);

CREATE INDEX idx_ac_class  ON asset_classifications(class);
CREATE INDEX idx_ac_status ON asset_classifications(status);

CREATE TRIGGER set_ac_updated_at
    BEFORE UPDATE ON asset_classifications
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- asset_content_link.method 확장 (filename / folder_path / tag 추가)
ALTER TABLE asset_content_link DROP CONSTRAINT asset_content_link_method_check;
ALTER TABLE asset_content_link ADD CONSTRAINT asset_content_link_method_check
    CHECK (method IN ('clip_similarity','ocr_text','manual','web_search',
                      'filename','folder_path','tag'));

-- M.2 워커 cursor
INSERT INTO sync_cursors (key, value)
VALUES ('asset_mapper_last_id', '0')
ON CONFLICT (key) DO NOTHING;
