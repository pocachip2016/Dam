# Step M.3: web-search-cache

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `plans/dev-meta-foundation/step0.md` — web_search_cache, web_search_quota 스키마
- `plans/dev-meta-foundation/index.json` → decisions.web_search
- `api/search.py` — API 엔드포인트 패턴

## 배경
KOBIS에 없는 컨텐츠(드라마, 해외 컨텐츠, 미분류)의 메타데이터를 웹서치로 보완한다.

우선순위 전략:
1. **내부 DB 우선** — content_titles에 이미 있으면 웹서치 생략
2. **캐시 히트** — web_search_cache에 동일 쿼리 있으면 API 호출 없이 반환
3. **신규 쿼터 사용** — 캐시 미스 + 월 쿼터 여유 있을 때만 실제 API 호출

무료 공급자 비교:
| 공급자 | 무료 쿼터 | 특이사항 |
|---|---|---|
| Brave Search API | 2,000/월 | JSON API, 별도 가입 필요 |
| SerpAPI | 100/월 | Google 결과, 소량 |
| DuckDuckGo (비공식) | 제한 없으나 불안정 | scraping, 불안정 |

→ **Brave Search API 기본**, SerpAPI 보조 (환경변수로 전환 가능)

## 작업

### `api/web_search.py` 작성

```python
class WebSearchClient:
    def __init__(self, conn, redis_client):
        self.provider = os.getenv('DAM_WEB_SEARCH_PROVIDER', 'brave')
        self.monthly_limit = int(os.getenv('DAM_WEB_SEARCH_MONTHLY_LIMIT', 2000))

    def search(self, query: str, force_fresh: bool = False) -> dict | None:
        # 1. 캐시 확인
        if not force_fresh:
            cached = self._get_cache(query)
            if cached:
                self._inc_hit(query)
                return cached

        # 2. 쿼터 확인
        if not self._has_quota():
            return None  # 쿼터 소진 시 None 반환, 호출자가 처리

        # 3. 실제 API 호출
        result = self._call_api(query)
        if result:
            self._save_cache(query, result)
            self._inc_quota()
        return result

    def _call_api(self, query: str) -> dict | None:
        if self.provider == 'brave':
            return self._brave_search(query)
        elif self.provider == 'serpapi':
            return self._serpapi_search(query)
        ...

    def get_quota_status(self) -> dict:
        # 현재 월 사용량/한도 반환
        ...
```

### `/quota` API 엔드포인트 추가 (api/main.py)
```
GET /quota
→ { "web_search": { "provider": "brave", "used": 42, "limit": 2000, "remaining": 1958 } }
```

### 캐시 만료 정책
- 컨텐츠 메타데이터: `expires_at = NULL` (영구)
- 실시간성 쿼리(박스오피스 등): `expires_at = now() + interval '7 days'`

## Acceptance Criteria
```bash
bash .claude/verify.sh M.3
```
- 동일 쿼리 2회 호출 시 `hit_count` 증가 확인 (`SELECT hit_count FROM web_search_cache LIMIT 1`)
- `GET /quota` 200 응답
- 쿼터 초과 시뮬레이션 → `None` 반환, DB 저장 없음 확인
- API 키 환경변수에만 존재

## 금지사항
- DuckDuckGo 비공식 스크래핑을 기본 공급자로 사용 금지 (불안정)
- 쿼터 확인 없이 무조건 API 호출 금지
- 웹서치 결과를 content_titles에 자동 INSERT 금지 — 캐시 테이블에만 저장
