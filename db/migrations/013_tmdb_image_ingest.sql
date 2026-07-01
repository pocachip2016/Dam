-- B.2.0: tmdb_image_ingest_log — TMDB 이미지 CAS ingest 감사 로그
--
-- mediaX tmdb_image_cache의 자연키(entity_type, tmdb_id, image_kind, file_path)를
-- 그대로 idempotency key로 사용. content_id/asset_content_link 없음 — 의도적으로
-- mediaX 콘텐츠에 미종속(다수의 TMDB 이미지가 아직 편성되지 않았기 때문).
-- 향후 서비스 콘텐츠로 채택될 경우 기존 asset_content_link(asset_id, content_id)
-- INSERT만으로 연결 가능 — 이 테이블 자체는 변경 불필요.

CREATE TABLE tmdb_image_ingest_log (
    id           BIGSERIAL PRIMARY KEY,
    entity_type  TEXT NOT NULL CHECK (entity_type IN ('movie', 'tv', 'person')),
    tmdb_id      INT  NOT NULL,
    image_kind   TEXT NOT NULL CHECK (image_kind IN ('poster', 'backdrop', 'logo', 'still', 'profile')),
    file_path    TEXT NOT NULL,           -- TMDB 상대 경로 (자연키 일부, 예: /abc123.jpg)
    source_url   TEXT NOT NULL,           -- 다운로드에 사용한 완전 CDN URL
    sha256       TEXT,                    -- 다운로드 후 계산
    asset_id     BIGINT REFERENCES assets(id) ON DELETE SET NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'downloaded', 'failed')),
    error_msg    TEXT,
    received_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

-- 자연키 기준 중복 ingest 방지
CREATE UNIQUE INDEX uq_tiil_natural_key
    ON tmdb_image_ingest_log (entity_type, tmdb_id, image_kind, file_path);
CREATE INDEX idx_tiil_status ON tmdb_image_ingest_log (status);

COMMENT ON TABLE tmdb_image_ingest_log IS
    'TMDB 이미지 → Dam tmdb_cas ingest 추적. mediaX 콘텐츠에 미종속(content_id 없음) — entity_type+tmdb_id 자연키로 멱등 보장.';
COMMENT ON COLUMN tmdb_image_ingest_log.file_path IS
    'TMDB API 상대 경로 — mediaX tmdb_image_cache와 동일 자연키 개념.';
