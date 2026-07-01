-- A.0: source_profiles — realm별 파싱·처리 프로파일
-- realm을 1급 시민으로: 워커가 이 테이블을 조회해 파싱 룰셋·폴더 depth를 결정한다.

-- asset_storage.realm CHECK에 tmdb_cas 추가
ALTER TABLE asset_storage
  DROP CONSTRAINT asset_storage_realm_check,
  ADD  CONSTRAINT asset_storage_realm_check CHECK (realm IN (
    'designfs',              -- 원본 NAS (인증된 원본)
    'designfs1_mirror',      -- NAS 미러 (원본 복제)
    'designfs1_derivatives', -- 서버측 파생물
    'dam_cas',               -- 로컬 content-addressed store
    'poc_sample',            -- 로컬 샘플
    'tmdb_cas'               -- TMDB 이미지 CAS (Plan B-2)
  ));

-- source_profiles: realm → 파싱 룰셋 매핑
CREATE TABLE source_profiles (
    realm        TEXT PRIMARY KEY,       -- asset_storage.realm 과 1:1 대응
    profile_key  TEXT NOT NULL,          -- 'genie_vod' | 'tmdb_cas' | 'generic'
    folder_depth INT  NOT NULL DEFAULT 2,-- 폴더트리 집계 깊이 (0 = 폴더 없음)
    parse_config JSONB NOT NULL DEFAULT '{}', -- 토크나이저 파라미터 (정규식, 연도범위 등)
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 시드: 현재 운영 중인 realm 전체
INSERT INTO source_profiles (realm, profile_key, folder_depth, notes) VALUES
  ('poc_sample',            'genie_vod', 2, 'KT 지니TV 디자인 NAS 샘플 (161k)'),
  ('designfs1_mirror',      'genie_vod', 2, 'KT 지니TV 디자인 NAS 미러 (167k)'),
  ('designfs',              'genie_vod', 2, '원본 NAS — 불변'),
  ('designfs1_derivatives', 'generic',   0, '파생물(썸네일 등) — 파싱 불필요'),
  ('dam_cas',               'generic',   0, '내부 CAS — 파싱 불필요'),
  ('tmdb_cas',              'tmdb_cas',  0, 'TMDB 이미지 CAS — 폴더 없음, 파싱 불필요');
