# Step M.1: kobis-ingest

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `plans/dev-meta-foundation/step0.md` — content_titles 스키마
- `ingest/ingest_local.py` — 기존 인제스트 패턴 참조
- `plans/dev-meta-foundation/index.json` → decisions.web_search

## 배경
KOBIS(영화진흥위원회) 오픈 API를 통해 영화 메타데이터를 수집한다. 무료 API키로 일 1,000건 기본 제공. 드라마는 KOBIS 범위 밖 → step M.7(kobis-expand)에서 검토.

KOBIS API 주요 엔드포인트:
- `http://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieList` — 목록
- `http://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo` — 상세

## 작업

### `ingest/kobis_crawler.py` 작성

```python
# 핵심 구조만 제시 — 구현은 에이전트 재량
class KobisCrawler:
    def __init__(self, api_key: str, conn, batch_size=100):
        ...

    def fetch_movie_list(self, year_from: int, year_to: int) -> list[dict]:
        # paginated fetch, rate-limit 준수 (0.1s 간격)
        ...

    def fetch_movie_detail(self, movie_cd: str) -> dict:
        # 감독·배우·장르 상세
        ...

    def upsert_titles(self, movies: list[dict]) -> int:
        # content_titles INSERT ON CONFLICT DO UPDATE
        # source='kobis', source_id=movieCd
        ...

    def run(self, year_from=2000, year_to=2026):
        # year 단위 루프, 진행 로그 출력
        ...
```

### 실행 스크립트
```bash
# 환경변수
DAM_KOBIS_API_KEY=<키>
DAM_DSN=postgresql://dam:dam@localhost:15432/dam

python ingest/kobis_crawler.py --year-from 2000 --year-to 2026
```

### 출력 로그
`dam_data/kobis_ingest.log` — 수집 건수·에러·소요시간 기록

### API 키 관리
- `docker-compose.yml` dam_api 서비스에 `DAM_KOBIS_API_KEY` 환경변수 추가
- `.env.local` (gitignore) 에 실제 키 보관 — 커밋 금지

## Acceptance Criteria
```bash
bash .claude/verify.sh M.1
```
- `SELECT count(*) FROM content_titles WHERE source='kobis';` → 1,000건 이상
- `SELECT title_ko, year, director FROM content_titles WHERE source='kobis' LIMIT 5;` — 정상 데이터 반환
- API 키 `.env.local` 에만 존재, 코드에 하드코딩 없음

## 금지사항
- API 키 코드·커밋에 포함하지 말 것
- 일 쿼터(1,000건) 초과 방지 — 첫 실행은 연도 범위를 좁게(2020~2026) 시작
- rate limit 없이 연속 호출 금지 (ban 위험)
