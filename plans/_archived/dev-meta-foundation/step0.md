# Step M.0: schema-foundation

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `db/migrations/` — 기존 마이그레이션 파일 패턴 확인
- `docs/ARCHITECTURE.md` — 현재 DB 스키마 구조

## 배경
현재 Dam DB는 assets·embeddings·tags·collections 중심. 외부 컨텐츠 메타데이터(영화·드라마 타이틀, 제작사, 감독, 방영년도 등)를 붙일 테이블이 없음. 이 step에서 메타 파운데이션 스키마를 확정하고 마이그레이션을 작성한다.

## 작업

### 신규 테이블 3개

```sql
-- 외부 소스에서 수집한 컨텐츠 타이틀 마스터
CREATE TABLE content_titles (
    id          SERIAL PRIMARY KEY,
    source      TEXT NOT NULL,          -- 'kobis', 'tmdb', 'iptv' 등
    source_id   TEXT NOT NULL,          -- 소스 고유 ID
    title_ko    TEXT NOT NULL,
    title_en    TEXT,
    content_type TEXT NOT NULL,         -- 'movie', 'drama', 'etc'
    year        INT,
    genre       TEXT[],
    director    TEXT[],
    nation      TEXT,
    raw_json    JSONB,                  -- 원본 API 응답 보존
    fetched_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(source, source_id)
);

-- 자산 ↔ 컨텐츠 타이틀 매핑
CREATE TABLE asset_title_links (
    id              SERIAL PRIMARY KEY,
    asset_id        BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    title_id        INT NOT NULL REFERENCES content_titles(id) ON DELETE CASCADE,
    match_method    TEXT NOT NULL,      -- 'clip_similarity', 'ocr_text', 'manual', 'web_search'
    confidence      FLOAT NOT NULL,     -- 0.0~1.0
    threshold_used  FLOAT,             -- 매핑 당시 threshold 기록
    confirmed       BOOLEAN DEFAULT FALSE, -- 수동 확인 여부
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(asset_id, title_id)
);

-- 웹서치 결과 캐시
CREATE TABLE web_search_cache (
    id          SERIAL PRIMARY KEY,
    query       TEXT NOT NULL UNIQUE,
    result_json JSONB NOT NULL,
    source      TEXT NOT NULL,         -- 'brave', 'serpapi', 'duckduckgo'
    hit_count   INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT now(),
    expires_at  TIMESTAMPTZ            -- NULL = 영구 캐시
);

-- 웹서치 쿼터 트래킹
CREATE TABLE web_search_quota (
    id          SERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    month       DATE NOT NULL,         -- 월 단위 (매월 1일)
    used_count  INT DEFAULT 0,
    limit_count INT NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(source, month)
);

-- 인덱스
CREATE INDEX ON content_titles(source, year);
CREATE INDEX ON content_titles USING gin(genre);
CREATE INDEX ON asset_title_links(asset_id);
CREATE INDEX ON asset_title_links(title_id);
CREATE INDEX ON asset_title_links(confidence);
CREATE INDEX ON web_search_cache(query);
CREATE INDEX ON web_search_cache(expires_at);
```

### 마이그레이션 파일
`db/migrations/009_meta_foundation.sql` 로 작성. 기존 파일 번호 패턴 확인 후 맞춤.

### 설정값 테이블 (또는 환경변수)
- `DAM_MAPPING_THRESHOLD=0.85` — 기본값, API로 런타임 변경 가능하게
- `DAM_WEB_SEARCH_PROVIDER=brave` — 기본 웹서치 공급자
- `DAM_WEB_SEARCH_MONTHLY_LIMIT=2000`

## Acceptance Criteria
```bash
bash .claude/verify.sh M.0
```
- 마이그레이션 적용 후 4개 테이블 존재 확인
- `SELECT table_name FROM information_schema.tables WHERE table_name IN ('content_titles','asset_title_links','web_search_cache','web_search_quota');` → 4행 반환

## 금지사항
- 기존 테이블(assets, embeddings 등) 컬럼 수정하지 말 것. 외래키 추가로만 연결.
- raw_json 컬럼에 데이터 정규화 강제하지 말 것 — 원본 보존이 목적.
