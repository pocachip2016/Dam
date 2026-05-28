# Step M.7: kobis-expand

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `plans/dev-meta-foundation/step1.md` — KobisCrawler 구조
- `plans/dev-meta-foundation/step0.md` — content_titles.content_type 컬럼
- `dam_data/kobis_ingest.log` — M.1 수집 결과 및 에러 현황

## 배경
M.1에서는 KOBIS 영화(movie) 데이터 기본 수집. 이 step에서 범위를 확대한다.

KOBIS API 추가 범위:
- **박스오피스 순위** (`searchDailyBoxOfficeList`, `searchWeeklyBoxOfficeList`) — 인기 영화 우선 처리
- **영화인 정보** (`searchPeopleList`) — 감독·배우 상세 (선택)
- **연도 범위 확대** — 1990년대까지 소급 수집

KOBIS 외 드라마 소스 검토:
| 소스 | 특이사항 |
|---|---|
| 한국방송통신위원회 | 방송 프로그램 DB, 공개 여부 불확실 |
| KMDB (한국영화데이터베이스) | 영화 특화, KOBIS와 중복 |
| TMDB | 영화+드라마, 무료 API(4만건/일) — 가장 현실적 |

→ **TMDB 연동 준비** (API 키 별도 발급): `source='tmdb'`로 content_titles 추가

## 작업

### `ingest/kobis_crawler.py` 확장
```python
def fetch_boxoffice(self, target_dt: str) -> list[dict]:
    # searchDailyBoxOfficeList → kobis_titles에 is_popular=True 마킹
    ...

def fetch_extended_years(self, year_from=1990, year_to=1999):
    # 기존 fetch_movie_list 재사용, 연도 범위만 확장
    ...
```

### `ingest/tmdb_crawler.py` 신규 작성 (드라마 포커스)
```python
class TmdbCrawler:
    BASE_URL = "https://api.themoviedb.org/3"

    def fetch_korean_tv(self, year: int) -> list[dict]:
        # /discover/tv?with_original_language=ko&first_air_date_year=year
        ...

    def fetch_movie(self, tmdb_id: int) -> dict:
        # /movie/{tmdb_id}?language=ko-KR&append_to_response=credits
        ...

    def upsert_titles(self, items: list[dict], content_type: str) -> int:
        # content_titles INSERT, source='tmdb'
        ...
```

### 수집 우선순위
1. KOBIS 박스오피스 Top 200 (연간) — 고우선, 자산 매핑 hit rate 높음
2. TMDB 한국 드라마 2010~2026
3. KOBIS 1990~1999 소급 (저우선)

### 일별 쿼터 관리
- KOBIS: 1,000/일 → 박스오피스 + 상세 분리 실행
- TMDB: 40,000/일 → 부담 없음, 단 rate limit 준수 (0.25s 간격)

## Acceptance Criteria
```bash
bash .claude/verify.sh M.7
```
- `SELECT source, count(*) FROM content_titles GROUP BY source;` → kobis + tmdb 양쪽 존재
- `SELECT count(*) FROM content_titles WHERE source='tmdb' AND content_type='drama';` → 100건 이상
- TMDB API 키 환경변수에만 존재, 코드 하드코딩 없음

## 금지사항
- TMDB 이미지 다운로드 금지 — 포스터·스틸 URL만 raw_json에 보존
- 쿼터 초과 방지 — 일별 수집량 상한을 스크립트 인자로 강제
- M.2 매핑 결과를 이 step에서 갱신하지 말 것 — 매핑 재실행은 M.6 remap API 사용
