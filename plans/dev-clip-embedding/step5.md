# Step 2.5: text-search-api

> GitHub: 미생성 | Milestone: clip-embedding

## 읽어야 할 파일
- `api/search.py` (`/similar/{id}` 패턴, `/stats` 의 hardcoded `'clip-vit-b32'`)
- `ingest/clip_worker.py` (텍스트 인코딩 함수 재사용 가능 시 분리)

## 작업
- `api/search.py` 에 `/search_text` 엔드포인트 추가:
  ```
  GET /search_text?q=<텍스트>&model=<clip-vit-b32|cn-clip-vitb16>&realm=poc_sample&limit=20
  ```
  - 텍스트 → CLIP 텍스트 임베딩 → cosine HNSW search
  - 모델 dispatch (open_clip / cn_clip 토크나이저 + text encoder)
  - 모델 캐시 위치 일관 (`MODEL_CACHE_DIR`)
- API 시작 시 두 텍스트 인코더 lazy-load (요청 첫 도달 시 로드)
- `/stats` 의 `embedded` 카운트를 모델별 분리:
  ```json
  {"by_realm": [{"realm":"poc_sample","embedded":{"clip-vit-b32":160036,"cn-clip-vitb16":160036}}]}
  ```
- `/similar/{id}` 에 `?model=` 쿼리 파라미터 추가 (default `clip-vit-b32`)
- `requirements-gpu.txt` 갱신 — API 도 동일 라이브러리 필요

## Acceptance Criteria
```bash
bash .claude/verify.sh 2.5
```
- `curl "http://localhost:18000/search_text?q=강아지&model=cn-clip-vitb16"` HTTP 200 + results ≥ 1
- `curl "http://localhost:18000/search_text?q=blue%20logo&model=clip-vit-b32"` HTTP 200 + results ≥ 1
- `curl "http://localhost:18000/similar/<id>?model=cn-clip-vitb16"` HTTP 200
- `/stats` 응답에 두 모델 임베딩 카운트 분리 표시

## 금지사항
- 텍스트 인코더를 매 요청마다 로드하지 마라. 이유: 모델 로드 오버헤드 ~수초, 응답 latency 폭증. 프로세스 전역 lazy-singleton.
- `0.0.0.0` 바인딩하지 마라. 이유: 로컬 검증 단계. 외부 노출은 별도 task.
