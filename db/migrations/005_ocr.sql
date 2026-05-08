-- Phase 3.6: OCR columns + tsvector index
ALTER TABLE assets
  ADD COLUMN IF NOT EXISTS ocr_text     TEXT,
  ADD COLUMN IF NOT EXISTS ocr_lang     TEXT,
  ADD COLUMN IF NOT EXISTS ocr_done_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS ocr_tsv      tsvector
    GENERATED ALWAYS AS (to_tsvector('simple', coalesce(ocr_text, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_assets_ocr_tsv ON assets USING GIN (ocr_tsv);
