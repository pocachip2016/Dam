-- Phase 3.5: tags + collections
-- Preserve existing path_inference data by renaming old asset_tags
ALTER TABLE asset_tags RENAME TO asset_tags_legacy;

CREATE TABLE tags (
  id          BIGSERIAL PRIMARY KEY,
  namespace   TEXT NOT NULL DEFAULT 'user',
  name        TEXT NOT NULL,
  created_by  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (namespace, name)
);

CREATE TABLE asset_tags (
  asset_id    BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  tag_id      BIGINT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  added_by    TEXT,
  added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, tag_id)
);
CREATE INDEX idx_asset_tags_tag ON asset_tags(tag_id);

CREATE TABLE collections (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  description TEXT,
  created_by  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (created_by, name)
);

CREATE TABLE collection_assets (
  collection_id BIGINT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  asset_id      BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  sort_order    INT,
  added_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (collection_id, asset_id)
);
CREATE INDEX idx_collection_assets_asset ON collection_assets(asset_id);
