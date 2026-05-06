# Step 3.4: search-filters

> GitHub: 미생성 | Milestone: mvp-features

## 읽어야 할 파일
- `api/search.py` (현재 `/search_text`, `/similar`, `/stats` 구조)
- `api/static/index.html` (현재 검색 UI)
- Step 3.2 결과 (folder_tokens, filename_tokens, year_hint, role_hint, metadata_json)

## 작업
- `/search_text` 쿼리 파라미터 추가:
  - `ext=jpg,png` — 다중 확장자 (CSV, primary_ext IN (...))
  - `folder=11.NEXT_UI` — folder_tokens GIN @> {token} 매칭 (다중 값은 모두 포함)
  - `role=poster,banner` — role_hint && {array} (다중 값은 OR)
  - `year_from=`, `year_to=` — year_hint 범위 (B-tree)
  - `size_min_mb=`, `size_max_mb=` — size_bytes 범위
  - `mtime_from=`, `mtime_to=` — ISO date 범위
- 추가 endpoint `/filename_search?q=<token>` — filename_tokens GIN @> 또는 trigram fallback
- SQL 빌더 분리 `api/search_filters.py`:
  - `build_filters(params: dict) -> (where_sql: str, sql_params: list)`
  - parameterized only (raw f-string SQL 금지)
- UI 사이드바 패널 (`api/static/index.html`):
  - 확장자 체크박스, 폴더 자동완성 select, role 체크박스, 연도 슬라이더, 사이즈 입력
  - 필터 변경 → 즉시 재검색 (debounce 300ms)
  - URL 파라미터 동기화 (브라우저 history.pushState — 공유 link)

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.4
```
- 5 시나리오 curl PASS:
  1. `/search_text?q=poster&ext=jpg` 200, 결과 모두 `.jpg`
  2. `/search_text?q=&folder=11.NEXT_UI` 200, 결과 folder_tokens 매칭
  3. `/search_text?q=character&role=poster` 200
  4. `/search_text?q=&year_from=2025&year_to=2025` 200
  5. `/search_text?q=&size_min_mb=10` 200, 결과 모두 ≥ 10 MB
- UI 사이드바 필터 동작 (수동 검증 OK)

## 금지사항
- 필터 간 OR 결합 금지 — 필터 간 AND, 다중 값 OR. 이유: 사용자 의도와 다름.
- 모든 필터를 GIN 만으로 처리하지 마라. 이유: year_hint·size_bytes 같은 스칼라는 B-tree.
- `LIKE '%token%'` 남발 금지. 이유: filename_tokens 가 이미 normalized 배열, GIN @> 사용.
- `/similar`, `/stats` 시그니처 변경 금지. 이유: 기존 UI 호환.
- raw string interpolation 으로 SQL 만들지 마라. 이유: SQL injection.
