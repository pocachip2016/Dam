# Step M.2: asset-mapping

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `plans/dev-meta-foundation/step0.md` — asset_title_links 스키마
- `plans/dev-meta-foundation/step1.md` — content_titles 데이터 구조
- `api/search.py` — 기존 CLIP 유사도 검색 패턴
- `plans/dev-meta-foundation/index.json` → decisions.dam_mapping_threshold (0.85)

## 배경
Dam 자산(160k 파일)에는 CLIP 임베딩이 이미 있다. content_titles 각 항목에 대해 타이틀명으로 CLIP 텍스트 임베딩을 생성하고, 자산 이미지 임베딩과 코사인 유사도를 계산해 threshold 이상이면 매핑한다.

추가로 OCR 텍스트에서 타이틀명이 감지되면 별도 match_method='ocr_text'로 기록.

## 작업

### `ingest/asset_mapper.py` 작성

```python
class AssetMapper:
    def __init__(self, conn, model, threshold: float = 0.85):
        self.threshold = threshold  # 런타임 변경 가능

    def encode_title(self, title: ContentTitle) -> np.ndarray:
        # CLIP 텍스트 인코딩: title_ko + year + genre 조합 프롬프트
        # 예: "영화 기생충 2019 드라마"
        ...

    def map_by_clip(self, title_id: int, title_vec: np.ndarray,
                    realm: str = 'poc_sample') -> int:
        # pgvector <=> 코사인 유사도로 상위 N개 자산 추출
        # confidence >= self.threshold 인 것만 asset_title_links INSERT
        # 반환: 매핑 건수
        ...

    def map_by_ocr(self, title_id: int, keywords: list[str]) -> int:
        # assets.ocr_text ILIKE '%keyword%' 로 보조 매핑
        # confidence = 0.70 고정 (텍스트 매칭은 낮게)
        ...

    def run(self, realm: str = 'poc_sample'):
        # content_titles 순회 → encode → map_by_clip → map_by_ocr
        # 진행 로그 dam_data/asset_mapping.log
        ...
```

### Threshold 설정
- 기본값 `DAM_MAPPING_THRESHOLD=0.85` (환경변수)
- step M.6(mapping-admin)에서 API로 런타임 변경 가능하게 구현
- threshold_used 컬럼에 매핑 당시 값 기록 → 나중에 재매핑 시 비교 가능

### 배치 전략
- content_titles를 연도별로 나눠 처리 (메모리 절약)
- pgvector 쿼리: `ORDER BY embedding <=> title_vec LIMIT 50` 후 Python에서 threshold 필터

## Acceptance Criteria
```bash
bash .claude/verify.sh M.2
```
- `SELECT count(*) FROM asset_title_links;` → 0 초과 (매핑 결과 존재)
- `SELECT avg(confidence) FROM asset_title_links WHERE match_method='clip_similarity';` → 0.85 이상
- `SELECT count(DISTINCT title_id) FROM asset_title_links;` — 최소 10개 타이틀 매핑

## 금지사항
- 전체 160k × 전체 타이틀 카테시안 프로덕트 in-memory 로드 금지 — pgvector ANN 활용
- confidence 0.85 미만 데이터 asset_title_links에 INSERT 금지 (조회 노이즈 방지)
- 기존 embeddings 테이블 수정 금지
