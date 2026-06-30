"""RunTracker unit tests — DB 연결 필요 (dam_postgres 컨테이너)."""
import time
import pytest
import psycopg

from ingest.run_tracker import RunTracker

DSN = "postgresql://dam:dam@localhost:15432/dam"


def _fetch_run(run_id: int) -> dict:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT worker_name, total_planned, processed, errors, finished_at, last_heartbeat"
                " FROM worker_runs WHERE id = %s",
                (run_id,),
            )
            row = cur.fetchone()
    assert row, f"run_id={run_id} not found"
    keys = ["worker_name", "total_planned", "processed", "errors", "finished_at", "last_heartbeat"]
    return dict(zip(keys, row))


def test_tracker_insert():
    """context manager 진입 시 row INSERT."""
    with RunTracker("test_insert", total_planned=100, dsn=DSN) as rt:
        run_id = rt.run_id
        assert run_id is not None
    row = _fetch_run(run_id)
    assert row["worker_name"] == "test_insert"
    assert row["total_planned"] == 100


def test_tracker_heartbeat():
    """tick() 호출 시 heartbeat 갱신."""
    with RunTracker("test_heartbeat", total_planned=200, dsn=DSN) as rt:
        rt.tick(50, force=True)
        run_id = rt.run_id
    row = _fetch_run(run_id)
    assert row["processed"] == 50
    assert row["last_heartbeat"] is not None


def test_tracker_finish():
    """종료 시 finished_at 기록."""
    with RunTracker("test_finish", total_planned=10, dsn=DSN) as rt:
        rt.tick(10, force=True)
        run_id = rt.run_id
    row = _fetch_run(run_id)
    assert row["finished_at"] is not None
    assert row["processed"] == 10


def test_tracker_errors():
    """오류 카운터 전달."""
    with RunTracker("test_errors", total_planned=50, dsn=DSN) as rt:
        rt.tick(40, errors=3, force=True)
        run_id = rt.run_id
    row = _fetch_run(run_id)
    assert row["errors"] == 3
