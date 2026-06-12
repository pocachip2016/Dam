# Step M.5: meta-search-api

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `api/search.py` — 기존 `/search_text`, `/similar` 엔드포인트
- `plans/dev-meta-foundation/step0.md` — content_titles, asset_title_links 스키마
- `api/static/index.html` — 웹 UI 구조

## 배경
M.1~M.2에서 content_titles와 asset_title_links가 채워졌다. 이제 이 메타데이터를 검색에 통합한다. 기존 `/search_text`에 메타 필터를 추가하고, 타이틀 기반 검색 엔드포인트를 신설한다.

## 작업

### 신규 엔드포인트: `GET /search_meta`

```
파라미터:
  title    str   — 타이틀명 부분 일치 (ILIKE)
  year     int   — 제작연도
  genre    str   — 장르
  source   str   — 'kobis', 'tmdb' 등
  realm    str   — 기본 'poc_sample'
  limit    int   — 기본 20

응답:
  {
    "results": [
      {
        "title_ko": "기생충",
        "year": 2019,
        "asset_count": 142,
        "sample_thumbnails": ["...path...", "...path..."],
        "avg_confidence": 0.91
      }
    ]
  }
```

### 기존 `/search_text` 확장
- `?title_id=<N>` 파라미터 추가: 특정 타이틀에 매핑된 자산만 필터

### 신규 엔드포인트: `GET /titles/{title_id}/assets`
```
타이틀에 연결된 자산 목록 (페이지네이션)
?limit=20&offset=0&min_confidence=0.85
```

### 웹 UI (`api/static/index.html`)
- 기존 검색창 아래 "타이틀별 탐색" 섹션 추가
- 타이틀 목록 카드 + 매핑 자산 수 표시
- 간단한 JS fetch, 별도 프레임워크 금지

## Acceptance Criteria
```bash
bash .claude/verify.sh M.5
```
- `GET /search_meta?title=기생충` → 200, results 배열 존재
- `GET /titles/{id}/assets` → 200, 자산 목록 반환
- 기존 `/search_text`, `/similar`, `/stats` 응답 변화 없음 (회귀 없음)

## 금지사항
- 기존 search.py 엔드포인트 시그니처 변경 금지
- 웹 UI에 외부 JS 라이브러리(React 등) 추가 금지 — vanilla JS 유지
