# Step 3.7: scale-validation

> GitHub: 미생성 | Milestone: designfs1-mirror

## 읽어야 할 파일
- `api/search.py` (`/search_text`, `/similar`, `/stats`)
- `db/migrations/002_embeddings.sql` (HNSW m=16, ef_construction=64)

## 작업
- 스케일 환경 검증 (~1.36M 벡터, 양 realm 합산):
  - HNSW EXPLAIN ANALYZE:
    ```sql
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT asset_id FROM embeddings
    WHERE model_name='clip-vit-b32'
    ORDER BY vector <=> '[...]'::vector LIMIT 20;
    ```
  - `Index Scan using idx_embeddings_hnsw` 확인
  - 실행 시간 측정
- API latency 벤치마크 (60회 반복):
  - `/search_text?q=logo` p50/p95
  - `/similar/{id}?model=clip-vit-b32` p50/p95
  - `/stats` p50 (집계 쿼리, 1.6M assets)
- 필요시 `ef_search` (`SET hnsw.ef_search`) 튜닝:
  - 기본 40 → 100 비교 (recall vs latency tradeoff)
- realm 다중 지원 검증:
  - `/search_text?realm=designfs1_mirror`
  - `/search_text?realm=poc_sample`
  - 결과 자산이 해당 realm 으로 필터링되는지
- `docs/phase3-perf.md` 작성: 표·EXPLAIN 출력·결정

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.7
```
- `/search_text` p95 < 100ms (디자인 에셋 검색 SLA)
- `/similar/{id}` p95 < 80ms
- HNSW Index Scan 확인 (Sequential Scan 이면 실패)
- `docs/phase3-perf.md` 존재

## 금지사항
- 인덱스를 REINDEX 하지 마라 (1.4M 벡터 = 수십 분, 불필요). 이유: HNSW 는 incremental insert 친화.
- realm 필터 없이 전체 검색을 default 로 만들지 마라. 이유: 사용자 의도와 다름, realm 격리 원칙.
- pg_stat 통계 부재로 EXPLAIN 신뢰도 낮을 수 있음 — 사전 `ANALYZE embeddings` 실행.
