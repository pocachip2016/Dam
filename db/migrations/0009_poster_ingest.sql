-- 0009: poster_ingest_log — mediaX → Dam 포스터 자동 등록 추적
--
-- mediaX에서 primary 포스터 지정 시 webhook으로 URL을 수신,
-- Dam이 직접 다운로드 후 assets 테이블에 등록하는 파이프라인의 감사 로그.
-- image_id (mediaX ContentImage.id) 기준 idempotent 처리.

CREATE TABLE poster_ingest_log (
    id             BIGSERIAL PRIMARY KEY,
    content_id     INT  NOT NULL REFERENCES content_catalog_mirror(content_id) ON DELETE CASCADE,
    image_id       INT  NOT NULL,           -- mediaX ContentImage.id (idempotency key)
    poster_source  TEXT NOT NULL
                   CHECK (poster_source IN ('tmdb', 'cp_upload', 'ai_generated', 'web_crawl')),
    source_url     TEXT NOT NULL,           -- 원본 URL (TMDB CDN 등)
    sha256         TEXT,                    -- 다운로드 후 계산
    asset_id       BIGINT REFERENCES assets(id) ON DELETE SET NULL,
    status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'downloaded', 'failed', 'skipped')),
    error_msg      TEXT,
    received_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at   TIMESTAMPTZ
);

-- image_id 기준 중복 등록 방지
CREATE UNIQUE INDEX uq_pil_image_id  ON poster_ingest_log (image_id);
CREATE INDEX idx_pil_content         ON poster_ingest_log (content_id);
CREATE INDEX idx_pil_status          ON poster_ingest_log (status);
CREATE INDEX idx_pil_received        ON poster_ingest_log (received_at DESC);

COMMENT ON TABLE poster_ingest_log IS
    'mediaX primary 포스터 → Dam 자동 등록 추적. image_id unique로 멱등 보장.';
COMMENT ON COLUMN poster_ingest_log.image_id IS
    'mediaX ContentImage.id — 동일 image_id 재요청 시 파일 재다운로드 생략';
COMMENT ON COLUMN poster_ingest_log.poster_source IS
    '소스 타입: tmdb(기본) | cp_upload | ai_generated | web_crawl — CHECK 확장으로 신규 소스 추가';
