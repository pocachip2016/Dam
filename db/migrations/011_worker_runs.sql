-- 011: worker_runs — 워커 실행 이력 및 진행률 추적
--
-- 워커(clip/metadata/hash/ocr/thumbnail/video)가 실행될 때마다
-- 한 row를 INSERT하고, tick() 마다 heartbeat+진행률을 UPDATE한다.
-- finished_at NULL = 진행 중 또는 비정상 종료.

CREATE TABLE worker_runs (
  id             BIGSERIAL PRIMARY KEY,
  worker_name    TEXT        NOT NULL,           -- 'clip','metadata','hash','ocr','thumbnail','scan'
  started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at    TIMESTAMPTZ,
  total_planned  INT,
  processed      INT         NOT NULL DEFAULT 0,
  errors         INT         NOT NULL DEFAULT 0,
  last_heartbeat TIMESTAMPTZ,
  notes          JSONB
);

CREATE INDEX idx_worker_runs_worker ON worker_runs(worker_name, started_at DESC);

COMMENT ON TABLE worker_runs IS
  '워커 실행 이력. finished_at NULL = 실행 중 또는 비정상 종료. heartbeat 5분 이상 미갱신 시 stale.';
