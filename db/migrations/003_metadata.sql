-- Phase 3.2: metadata columns + GIN indexes
ALTER TABLE assets
  ADD COLUMN IF NOT EXISTS metadata_json   JSONB,
  ADD COLUMN IF NOT EXISTS folder_tokens   TEXT[],
  ADD COLUMN IF NOT EXISTS filename_tokens TEXT[],
  ADD COLUMN IF NOT EXISTS year_hint       INT,
  ADD COLUMN IF NOT EXISTS role_hint       TEXT[];

CREATE INDEX IF NOT EXISTS idx_assets_folder_tokens   ON assets USING GIN (folder_tokens);
CREATE INDEX IF NOT EXISTS idx_assets_filename_tokens ON assets USING GIN (filename_tokens);
CREATE INDEX IF NOT EXISTS idx_assets_year_hint       ON assets (year_hint);
CREATE INDEX IF NOT EXISTS idx_assets_role_hint       ON assets USING GIN (role_hint);
