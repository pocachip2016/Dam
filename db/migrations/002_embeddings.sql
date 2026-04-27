-- 002_embeddings.sql
-- Phase 2 확장: 벡터 임베딩 테이블 + HNSW 인덱스
--
-- 적용:
--   psql postgresql://dam:dam@localhost:15432/dam -f db/migrations/002_embeddings.sql

-- =============================================================
-- 1. 임베딩 테이블
-- =============================================================
-- CLIP ViT-B/32 → 512차원 / ViT-L/14 → 768차원
-- model_name 컬럼으로 복수 모델 병존 가능
CREATE TABLE IF NOT EXISTS embeddings (
    asset_id    BIGINT    NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    model_name  TEXT      NOT NULL,           -- 예: 'clip-vit-b32', 'clip-vit-l14'
    vector      vector(512),                  -- 기본 모델(ViT-B/32) 용
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, model_name)
);

-- =============================================================
-- 2. HNSW 인덱스 (코사인 유사도)
-- =============================================================
-- m=16: 그래프 연결수 (기본값). ef_construction=64: 색인 품질.
-- 81K 벡터 기준 메모리 ~200MB 예상.
CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw
    ON embeddings USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- =============================================================
-- 3. 썸네일 경로 컬럼 (assets에 추가)
-- =============================================================
ALTER TABLE assets
    ADD COLUMN IF NOT EXISTS thumbnail_path TEXT;

COMMENT ON COLUMN assets.thumbnail_path IS
    '로컬 썸네일 절대 경로. thumbnail_worker.py가 채움.';

-- =============================================================
-- 4. 임베딩 진행 상태 뷰
-- =============================================================
CREATE OR REPLACE VIEW v_embedding_status AS
SELECT
    s.realm,
    COUNT(DISTINCT s.asset_id)                          AS total_assets,
    COUNT(DISTINCT e.asset_id)                          AS embedded,
    COUNT(DISTINCT s.asset_id) - COUNT(DISTINCT e.asset_id) AS pending
FROM asset_storage s
LEFT JOIN embeddings e ON e.asset_id = s.asset_id AND e.model_name = 'clip-vit-b32'
GROUP BY s.realm;

COMMENT ON VIEW v_embedding_status IS
    'realm별 CLIP 임베딩 완료/미완료 집계. clip_worker.py 진행 모니터링용.';
