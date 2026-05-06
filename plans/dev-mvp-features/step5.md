# Step 3.5: tags-collections

> GitHub: 미생성 | Milestone: mvp-features

## 읽어야 할 파일
- `db/migrations/001_init.sql` (asset_tags 컨셉 — "분류는 태그로" 코멘트)
- `api/search.py` 및 Step 3.4 검색 필터 패턴

## 작업
- 마이그레이션 `db/migrations/004_tags_collections.sql`:
  ```sql
  CREATE TABLE tags (
    id          BIGSERIAL PRIMARY KEY,
    namespace   TEXT NOT NULL DEFAULT 'user',  -- 'user' | 'system' | 'auto'
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
  ```
- 다중 사용자 가정 — Phase 4 auth 전까지는 `X-User: <username>` 헤더로 식별 (placeholder)
- API endpoints:
  - `api/tags.py`:
    - `GET /tags?prefix=&limit=` — 자동완성
    - `POST /assets/{id}/tags` body `{"name":"우영우","namespace":"user"}` — 멱등 (있으면 reuse)
    - `DELETE /assets/{id}/tags/{tag_id}`
    - 정책: `namespace='user'` tag 의 마지막 asset 연결 제거 시 tag row 도 삭제 (orphan 청소). 다른 namespace 보존.
  - `api/collections.py`:
    - `GET /collections?owner=` / `POST /collections` / `DELETE /collections/{id}`
    - `POST /collections/{id}/assets` body `{"asset_ids":[1,2,3]}`
    - `DELETE /collections/{id}/assets/{asset_id}`
- `/search_text` 에 `tag=우영우,포스터` 추가 (Step 3.4 필터 패턴 일관)
- UI 추가:
  - 자산 상세 패널 — tag chip + 추가 input (자동완성)
  - 사이드바 "내 컬렉션" 트리 (사용자 별), 클릭 시 그리드 전환
  - 다중 선택 (Shift+click) → "컬렉션에 일괄 추가" 버튼

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.5
```
- 시나리오: tag 부착 (POST 201) → `/search_text?tag=...` 결과 포함 → 제거 (DELETE 204) PASS
- collection 생성 → 다수 asset 추가 → 조회 시 sort_order 보존
- 동시 사용자 시뮬레이션 (X-User: alice / bob 같은 자산 동시 태깅) → 둘 다 보존, conflict 없음

## 금지사항
- tag.namespace='system' 또는 'auto' 자동 삭제 금지. 이유: 사용자 의도된 시스템 태그 보호.
- collection asset 순서를 client 측만 관리 금지. 이유: 다중 클라이언트 동기화 불가. sort_order DB 저장.
- 검색 필터 파라미터 형식을 Step 3.4 와 다르게 만들지 마라. 이유: 일관성.
- X-User 헤더를 prod 에 그대로 두지 마라 (Phase 4.2 auth 가 교체). 이유: 인증 우회 가능.
