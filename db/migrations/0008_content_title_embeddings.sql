-- M.3: content title embedding cache (clip-vit-b32 text encoder)
CREATE TABLE content_title_embeddings (
    content_id  INT NOT NULL REFERENCES content_catalog_mirror(content_id) ON DELETE CASCADE,
    model_name  TEXT NOT NULL,
    vector      vector(512) NOT NULL,
    encoded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (content_id, model_name)
);

CREATE INDEX idx_cte_model ON content_title_embeddings(model_name);

-- M.3 워커 cursor
INSERT INTO sync_cursors (key, value)
VALUES ('clip_text_mapper_last_id', '0')
ON CONFLICT (key) DO NOTHING;
