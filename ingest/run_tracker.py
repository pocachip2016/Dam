"""worker_runs DB 연동 context manager.

사용 예:
    with RunTracker("metadata", total_planned=161030) as rt:
        for batch in batches:
            process(batch)
            rt.tick(processed=rt.processed + len(batch), errors=rt.errors)
"""

import os
import logging
from datetime import datetime, timezone

import psycopg

DAM_DSN = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")

log = logging.getLogger(__name__)


class RunTracker:
    def __init__(self, worker_name: str, total_planned: int | None = None, dsn: str = DAM_DSN):
        self.worker_name = worker_name
        self.total_planned = total_planned
        self.dsn = dsn
        self.run_id: int | None = None
        self.processed = 0
        self.errors = 0
        self._tick_counter = 0

    def __enter__(self) -> "RunTracker":
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO worker_runs(worker_name, total_planned, last_heartbeat)"
                    " VALUES(%s, %s, now()) RETURNING id",
                    (self.worker_name, self.total_planned),
                )
                self.run_id = cur.fetchone()[0]
            conn.commit()
        log.info("RunTracker start worker=%s run_id=%s total=%s",
                 self.worker_name, self.run_id, self.total_planned)
        return self

    def tick(self, processed: int, errors: int = 0, force: bool = False):
        """진행 카운터 갱신. 100회마다 또는 force=True 시 DB 업데이트."""
        self.processed = processed
        self.errors = errors
        self._tick_counter += 1
        if force or self._tick_counter % 100 == 0:
            self._flush()

    def _flush(self):
        if self.run_id is None:
            return
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE worker_runs SET processed=%s, errors=%s, last_heartbeat=now()"
                    " WHERE id=%s",
                    (self.processed, self.errors, self.run_id),
                )
            conn.commit()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.run_id is None:
            return
        self._flush()
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE worker_runs SET finished_at=now(), processed=%s, errors=%s WHERE id=%s",
                    (self.processed, self.errors, self.run_id),
                )
            conn.commit()
        log.info("RunTracker finish worker=%s run_id=%s processed=%s errors=%s",
                 self.worker_name, self.run_id, self.processed, self.errors)
        return False  # 예외 전파
