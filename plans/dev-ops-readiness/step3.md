# Step 4.3: monitoring

> GitHub: 미생성 | Milestone: ops-readiness

## 읽어야 할 파일
- `ingest/scan_worker.py`, `clip_worker.py`, `metadata_worker.py`, `hash_worker.py`, `ocr_worker.py` (로깅 패턴)

## 작업
- 마이그레이션 `db/migrations/007_worker_runs.sql`:
  ```sql
  CREATE TABLE worker_runs (
    id             BIGSERIAL PRIMARY KEY,
    worker_name    TEXT NOT NULL,    -- 'clip','metadata','hash','ocr','thumbnail','scan'
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    total_planned  INT,
    processed      INT NOT NULL DEFAULT 0,
    errors         INT NOT NULL DEFAULT 0,
    last_heartbeat TIMESTAMPTZ,
    notes          JSONB
  );
  CREATE INDEX idx_worker_runs_worker ON worker_runs(worker_name, started_at DESC);
  ```
- 모든 worker 가:
  - 시작 시 row INSERT (worker_name, total_planned)
  - 100 batch 마다 UPDATE (processed, errors, last_heartbeat=now())
  - 종료 시 finished_at 채움
  - 공통 모듈 `ingest/run_tracker.py` (with-context manager)
- 로깅 표준화: stdlib logging + JSON formatter
  - `{"ts":..., "worker":..., "level":..., "asset_id":..., "msg":...}`
- `api/admin.py` (admin role only):
  - `GET /admin/workers` — 최근 N개 run + 진행률 + ETA (linear extrapolation)
  - `GET /admin/workers/{id}` — 단일 run 상세
  - `GET /admin/workers/{id}/log?lines=200` — 파일 tail (옵션)
- UI `api/static/admin.html`:
  - 워커 카드 grid (name / progress bar / errors / ETA / heartbeat age)
  - 60s 자동 새로고침 (admin 만 접근, login 후 navigate)
  - 에러 카운트 추이 (최근 24h, 시간 단위 bar chart)
- `/health` endpoint (`api/main.py`) 기본형 추가:
  - `SELECT 1` 확인 → 200 / 503
  - 무인증 접근 가능 (의도적 — Caddy/k8s 헬스 프로브용)

## Acceptance Criteria
```bash
bash .claude/verify.sh 4.3
```
- 워커 1개 (예: metadata_worker dummy run) 실행 → `worker_runs` row 생성 + heartbeat 갱신
- `/admin/workers` admin 200, viewer 403
- `/health` 무인증 200, DB stop 시 503
- admin 대시보드 UI 진행률 표시 (수동 검증)

## 금지사항
- worker_runs 에 INSERT 만 하고 UPDATE 안 하지 마라. 이유: heartbeat 없으면 stale detect 불가.
- 로그를 파일에만 쓰고 worker_runs 동기화 안 하지 마라. 이유: dashboard 가 DB 만 읽음.
- 진행률 계산이 무거운 쿼리를 매 request 호출 금지. 이유: dashboard polling × 사용자 수 = DB 부하.
- `/health` 에 DB write 또는 무거운 쿼리 포함 금지. 이유: liveness 만, readiness 별도 endpoint.
