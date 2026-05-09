# Step M.2: asset-classification-and-mapping

> GitHub: 미생성 | Milestone: dev-asset-content-mapping

## 배경 (실측 데이터 기반 plan 보강)

161,030 자산 (dam_poc_sample) 분석 결과:
- 콘텐츠 자산: 약 110k (`@디자인산출물_가로포스터+단편상세`, `@디자인산출물_오픈VOD`)
- 슬라이스(컴포넌트 분해): 약 46k (`슬라이스/@슬라이스` 폴더)
- 프로모션/캠페인: 약 13k (`_프로모션_`, `01_첫화면빅배너`)
- 인물명 폴더(예: `장희진`): **디자이너 워크스페이스** — 배우 아님 (mediaX person_master 0건 + 폴더 내부 다양한 작품 자산)
- filename에 콘텐츠명 명시: `[NEXT_VOD빅배너_IMG]1760x600_조선정신과의사유세풍2.jpg` — CLIP보다 압도적으로 강한 시그널
- mediaX는 포스터를 외부 URL로만 보유 → image-to-image 매칭 불가 → 텍스트 시그널 우선

핵심 결정:
- **분류와 매핑을 단일 워커에서 처리** (한 번 스캔으로 효율↑, 분류 결과로 매핑 candidate 좁힘)
- 콘텐츠가 아닌 자산도 별도 관리 필요 → `asset_classifications` 테이블 신설
- multi-class 허용 (`첫화면빅배너_기생충.jpg` → promotion + content)
- 디자이너 폴더는 분류 시그널 아님 — 폴더는 통과시키고 안의 파일이 자체 filename으로 매핑

## 읽어야 할 파일
- `db/migrations/006_content_mapping.sql` — 기존 asset_content_link 스키마
- `ingest/metadata_worker.py` — folder_tokens/filename_tokens/year_hint/role_hint 추출 로직
- `ingest/mediax_mirror.py` — content_catalog_mirror 적재 패턴 참조
- mediaX `backend/api/meta_core/intelligence/router.py` — 인덱스 엔드포인트 패턴 참조 (이번 step과 무관)

## 작업

### 1. 신규 마이그레이션 `db/migrations/0007_asset_classifications.sql`

```sql
-- asset_classifications: multi-class 자산 분류
CREATE TABLE asset_classifications (
    asset_id        BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    class           TEXT NOT NULL CHECK (class IN (
                       'content','promotion','seasonal','pricing','branding',
                       'ui_service','composition','draft','unclassified')),
    sub_class       TEXT,             -- 'seasonal'→'추석', 'promotion'→'home_banner' 등
    confidence      REAL,
    method          TEXT NOT NULL CHECK (method IN (
                       'folder_pattern','filename_keyword','role_hint',
                       'tag','manual','rule')),
    matched_signal  TEXT,             -- 매칭된 폴더명/키워드 (감사 추적)
    status          TEXT NOT NULL DEFAULT 'candidate'
                    CHECK (status IN ('candidate','confirmed','rejected')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, class)
);
CREATE INDEX idx_ac_class  ON asset_classifications(class);
CREATE INDEX idx_ac_status ON asset_classifications(status);

CREATE TRIGGER set_ac_updated_at
    BEFORE UPDATE ON asset_classifications
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- asset_content_link.method 확장 (filename / folder_path / tag 추가)
ALTER TABLE asset_content_link DROP CONSTRAINT asset_content_link_method_check;
ALTER TABLE asset_content_link ADD CONSTRAINT asset_content_link_method_check
    CHECK (method IN ('clip_similarity','ocr_text','manual','web_search',
                      'filename','folder_path','tag'));

-- M.2 워커 cursor (idempotent 재처리 지원)
INSERT INTO sync_cursors (key, value)
VALUES ('asset_mapper_last_id', '0')
ON CONFLICT (key) DO NOTHING;
```

### 2. 신규 `ingest/_classification_rules.py`

```python
import re

# (regex, class, sub_class, confidence)
FOLDER_PATTERNS: list[tuple[re.Pattern, str, str | None, float]] = [
    (re.compile(r'@?디자인산출물_(가로포스터|단편상세|오픈VOD)'), 'content',     None, 0.95),
    (re.compile(r'(_프로모션_|기획전|캠페인|03_프로모션_콘텐츠유형)'), 'promotion',   None, 0.92),
    (re.compile(r'(01_첫화면빅배너|고도화배너)'),               'promotion',   'home_banner', 0.90),
    (re.compile(r'(_메뉴|컨테이너_메뉴)'),                       'ui_service',  'menu', 0.95),
    (re.compile(r'(슬라이스|@슬라이스|03_IMG)'),                'composition', None, 0.90),
    (re.compile(r'(시안|draft|wip|^old$)'),                    'draft',       None, 0.85),
    (re.compile(r'■영화'),                                     'content',     'movie', 0.85),
    (re.compile(r'■(해외|국내)?시리즈'),                        'content',     'series', 0.85),
]

FILENAME_KEYWORDS: dict[str, list[str]] = {
    'seasonal':  ['추석','설날','크리스마스','여름','겨울','봄','가을','신년','연말','발렌타인','할로윈','명절','구정','어버이날'],
    'pricing':   ['할인','세일','쿠폰','특가','1+1','sale','discount'],
    'promotion': ['이벤트','캠페인','마케팅','프로모','광고','기획전','특별전'],
    'branding':  ['로고','logo','심볼','CI','BI'],
}
```

### 3. 신규 `ingest/_korean_norm.py`

```python
import re

KOREAN = re.compile(r'[가-힣]+')
NON_ALNUM = re.compile(r'[^0-9a-zA-Z가-힣]+')

def extract_korean(text: str) -> list[str]:
    """파일명에서 한글 substring만 추출 — 토큰화 깨짐 회피."""
    return KOREAN.findall(text)

def normalize_title(text: str) -> str:
    """공백/구두점 제거 후 소문자."""
    return NON_ALNUM.sub('', text).lower()
```

### 4. 신규 `ingest/asset_mapper.py` — oneshot 워커

시그니처 (구현은 에이전트 재량):
```python
def classify_asset(asset_row, rules) -> list[Classification]: ...
def match_content(asset_row, content_index, threshold) -> list[ContentMatch]: ...
def main():
    """ENV 읽고 → DB 연결 → batch fetch → classify → match → UPSERT → cursor 갱신."""
```

처리 절차 (per asset, batch 1000):
1. **폴더 패턴 매칭** → 매칭된 모든 패턴 → asset_classifications UPSERT (multi-class)
2. **filename 키워드 매칭** → seasonal/pricing/promotion/branding 보강
3. **role_hint=['logo']** 단독 → branding 클래스
4. **콘텐츠 매핑 시도** (조건부):
   - composition / ui_service / draft 클래스만 있는 자산 → **스킵**
   - 시도 자산: content 클래스 또는 role_hint ∈ {poster, banner, detail}
   - 4축 시그널 (max score):
     - `tag` (0.95~1.0): asset_tags ↔ content title
     - `filename` (0.85~0.98): `extract_korean(filename)` substring/fuzzy ↔ content.title/original_title
     - `folder_path` (0.85~0.92): folder_tokens 한글 ↔ content title
     - `ocr_text` (0.85~0.92): rapidfuzz ratio ↔ content title
   - 보너스: year_hint == production_year (+0.05) / ±1년 (+0.02)
   - threshold ≥ 0.85 → asset_content_link UPSERT + 'content' 클래스 추가
5. **모두 fail** → 'unclassified' 클래스
6. cursor (`asset_mapper_last_id`) atomic 갱신 — 재실행 idempotent

환경변수:
- `DAM_DSN` (필수)
- `DAM_MAPPING_THRESHOLD` (0.85)
- `DAM_MAPPING_BATCH` (1000)
- `DAM_FUZZY_RATIO` (0.88)
- `DAM_SKIP_NON_CONTENT_MAPPING` (true)

### 5. 신규 `api/mapping.py` — read-only 통계/조회 API

엔드포인트 4개:
- `GET /api/mapping/stats` — class 분포 + 매핑 적중률 + confidence 히스토그램 + method 비중
- `GET /api/mapping/by-content/{content_id}` — 특정 콘텐츠 매핑 자산 (썸네일 path + confidence + method + status)
- `GET /api/mapping/by-class/{class}?status=&page=&size=` — class별 자산 페이징
- `GET /api/mapping/asset/{asset_id}` — 자산 단건 분류·매핑 detail

### 6. 신규 화면: 매핑 대시보드 (read-only)

`api/web/templates/admin/mapping-dashboard.html` (또는 기존 admin 템플릿 패턴 따라):
- class 분포 도넛 차트
- 매핑 적중률 (콘텐츠 자산 중 매핑 성공 비율)
- confidence 히스토그램 (0.85~0.90 / 0.90~0.95 / 0.95~1.00)
- method 비중
- 콘텐츠별 매핑 수 TOP10 + 매핑 0건 콘텐츠 목록

(라우터 등록은 기존 `api/main.py`에 include)

### 7. 의존성 추가
- `requirements.txt` 에 `rapidfuzz` 추가

### 8. 테스트
- `tests/test_asset_mapper.py` — 픽스처: asset 20건 + content 10건 → 분류·매핑 결과 검증
- `tests/test_mapping_api.py` — 4개 엔드포인트 200 응답
- `tests/test_classification_rules.py` — 정규식 단위 테스트

### 9. cron 등록 (verify 후 수동)
```bash
0 4 * * * cd /home/ktalpha/Work/Dam && \
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
  .venv/bin/python -m ingest.asset_mapper >> dam_data/asset_mapping.log 2>&1
```

## Acceptance Criteria
```bash
bash .claude/verify.sh M.2
```

검증 항목:
- 0007 마이그레이션 적용 후 asset_classifications 테이블 존재
- 워커 1회 실행 후 분류 분포:
  - unclassified ≤ 10,000건
  - content 클래스 ≥ 95,000건
  - composition 클래스 ≥ 40,000건
- content 클래스 자산 중 asset_content_link 적중 ≥ 70%
- read-only API 4개 엔드포인트 200 응답
- 대시보드 페이지 HTML 렌더링 정상
- pytest 신규 테스트 전통과
- 워커 재실행 idempotent (행 수 변동 없음, UPDATE만)

## 금지사항
- daemon/loop 금지 — oneshot
- assets 테이블 컬럼 추가/수정 금지 — asset_classifications 별도 테이블
- status='confirmed' 자동 설정 금지 — M.6 admin 후 인간 승인
- write API 금지 — 이번 step은 read-only (confirm/reject/reclass는 M.6)
- 디자이너 폴더에 person_asset 같은 클래스 부여 금지 (실측 결과 무관 — 폴더는 메타정보일 뿐)
- ui_service / composition / draft 자산에 콘텐츠 매핑 시도 금지 (false positive 예방)
- filename_tokens 컬럼 사용 금지 — 한글 단어 깨짐 (`'케빈, 넌'` → `['너]케','빈,']`). assets.filename 원본에서 `extract_korean()` 사용

## 화면 5개 — 후속 step 참조

| 화면 | 위치 | step | 비고 |
|------|------|------|------|
| 분류 검토 (confirm/reject/reclass) | `/admin/classification` | M.6 | write |
| 콘텐츠 매핑 검토 | `/admin/content-mapping` | M.6 | write |
| 미분류 자산 처리 | `/admin/unclassified` | M.6 | write |
| **매핑 대시보드 (read-only)** | `/admin/mapping-dashboard` | **M.2 (이번)** | read-only |
| 사용자/큐레이터 검색 | `/search?class=...&content_id=...` | M.5 | filter 확장 |
