"""
mediaX content mirror worker (oneshot).

환경변수:
  DAM_DSN           postgres DSN (필수)
  MEDIAX_URL        mediaX 베이스 URL (기본: http://localhost:8000)
  DAM_MEDIAX_LIMIT  per-page limit (기본: 500, max 1000)
  DAM_MEDIAX_TIMEOUT HTTP 타임아웃 초 (기본: 30)

실행:
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam python -m ingest.mediax_mirror
"""
import logging
import os
from datetime import datetime, timezone

import httpx
import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_UPSERT_SQL = """
INSERT INTO content_catalog_mirror
  (content_id, title, original_title, content_type,
   production_year, status, mx_updated_at, synced_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (content_id) DO UPDATE SET
  title           = EXCLUDED.title,
  original_title  = EXCLUDED.original_title,
  content_type    = EXCLUDED.content_type,
  production_year = EXCLUDED.production_year,
  status          = EXCLUDED.status,
  mx_updated_at   = EXCLUDED.mx_updated_at,
  synced_at       = now();
"""


def _read_cursor(conn: psycopg.Connection, key: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM sync_cursors WHERE key=%s", (key,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def _write_cursor(conn: psycopg.Connection, key: str, value: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE sync_cursors SET value=%s, updated_at=now() WHERE key=%s",
            (value, key),
        )


def _upsert_batch(conn: psycopg.Connection, items: list[dict]) -> None:
    rows = []
    for item in items:
        updated_at_str = item.get("updated_at") or ""
        try:
            mx_updated_at = datetime.fromisoformat(updated_at_str)
            if mx_updated_at.tzinfo is None:
                mx_updated_at = mx_updated_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            mx_updated_at = datetime.now(tz=timezone.utc)
        rows.append((
            item["content_id"],
            item["title"],
            item.get("original_title"),
            item["content_type"],
            item.get("production_year"),
            item["status"],
            mx_updated_at,
        ))
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, rows)


def main() -> None:
    dsn = os.environ["DAM_DSN"]
    base = os.environ.get("MEDIAX_URL", "http://localhost:8000").rstrip("/")
    limit = int(os.environ.get("DAM_MEDIAX_LIMIT", "500"))
    timeout = float(os.environ.get("DAM_MEDIAX_TIMEOUT", "30"))

    with psycopg.connect(dsn, autocommit=False) as conn:
        cur_ts = _read_cursor(conn, "content_mirror_next_ts")
        log.info("start cursor=%d", cur_ts)

        total = 0
        with httpx.Client(timeout=timeout) as client:
            while True:
                r = client.get(
                    f"{base}/api/meta-core/contents/since",
                    params={"ts": cur_ts, "limit": limit},
                )
                r.raise_for_status()
                page = r.json()
                items = page.get("items", [])
                next_ts = page.get("next_ts")

                if items:
                    _upsert_batch(conn, items)
                    total += len(items)

                new_cur = next_ts if next_ts is not None else cur_ts
                _write_cursor(conn, "content_mirror_next_ts", str(new_cur))
                conn.commit()

                if len(items) < limit or new_cur == cur_ts:
                    break
                cur_ts = new_cur

        log.info("done synced=%d cursor=%s", total, new_cur)


if __name__ == "__main__":
    main()
