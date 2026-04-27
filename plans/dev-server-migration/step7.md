# Step 7: api-smoke

> GitHub: 미생성 | Milestone: server-migration

## 읽어야 할 파일
- `api/search.py` (DB_DSN 환경변수, 엔드포인트 목록)
- `plans/dev-server-migration/index.json`

## 작업
- API 기동: `.venv/bin/python api/search.py` (포트 18000)
- 검증:
  - `curl -fsS http://localhost:18000/stats` → poc_sample 통계 JSON
  - `curl -fsS "http://localhost:18000/search?q=.jpg&realm=poc_sample&limit=5"` → hits ≥ 1
  - `curl -fsS http://localhost:18000/asset/<asset_id>` → 자산 상세
  - `curl -I http://localhost:18000/thumb/<asset_id>` → 200 image/jpeg
- 결과를 `docs/migration-status.md` 의 "이관 후 검증" 섹션에 기록

## Acceptance Criteria
```bash
bash .claire/verify.sh 1.7
```
- `curl -fsS http://localhost:18000/stats` 200 + JSON 에 `poc_sample` 키
- `curl -fsS "http://localhost:18000/search?q=.jpg&limit=5"` hits ≥ 1

## 금지사항
- `0.0.0.0` 바인딩으로 외부 노출하지 마라. 이유: 이번 단계는 로컬 검증만, 인증 없이 외부 노출 금지.
- 검증 전 DB 가 비어있는지 확인하지 않고 스모크 테스트 통과 처리하지 마라. 이유: step 6 완료가 전제 조건.
