#!/usr/bin/env python3
"""Phase 2 로컬 파일스캔 → PostgreSQL 적재

poc_sample 디렉토리를 os.walk로 스캔해서 realm='poc_sample'로 적재.
ingest_inventory.py와 동일한 스키마(assets + asset_storage + asset_tags + scan_runs).

설치:
  pip install psycopg[binary]

실행:
  python ingest/ingest_local.py
  POC_ROOT=/mnt/d/dam_analysis/poc_sample DAM_DSN="..." python ingest/ingest_local.py
"""

import os, sys, time, logging, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

try:
    import psycopg
except ImportError:
    sys.exit('psycopg 미설치. 실행: pip install psycopg[binary]')

POC_ROOT = os.environ.get('POC_ROOT',  '/mnt/d/dam_analysis/poc_sample')
DB_DSN   = os.environ.get('DAM_DSN',   'postgresql://dam:dam@localhost:15432/dam')
REALM    = 'poc_sample'
BATCH    = 5000

SKIP_PREFIXES = ('._', '~$', '_')  # macOS 리소스포크, Office 임시, robocopy 로그 등


def parse_path(full_path: str):
    """절대경로 → (top_folder, sub_folder, filename, ext)"""
    root = POC_ROOT.rstrip('/')
    rel  = full_path[len(root) + 1:] if full_path.startswith(root + '/') else full_path
    parts = rel.split('/')
    fname = parts[-1]
    top   = parts[0] if len(parts) >= 2 else None
    sub   = parts[1] if len(parts) >= 3 else None
    _, ext = os.path.splitext(fname.lower())
    return top, sub, fname, ext or None


def walk_files():
    """poc_sample 아래 모든 파일을 (path, size_bytes, mtime) 로 yield"""
    root = POC_ROOT
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if any(fname.startswith(p) for p in SKIP_PREFIXES):
                continue
            full = os.path.join(dirpath, fname)
            try:
                st = os.stat(full)
            except OSError:
                continue
            mtime = datetime.datetime.fromtimestamp(st.st_mtime, tz=datetime.timezone.utc)
            yield full, st.st_size, mtime


def ingest(conn) -> dict:
    log.info(f'poc_sample 스캔 시작: {POC_ROOT}')
    t0 = time.time()

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO scan_runs (realm, source_root, notes)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id
        """, (REALM, POC_ROOT, '{"phase": "2", "type": "local_walk"}'))
        run_id = cur.fetchone()[0]

        cur.execute("""
            CREATE TEMP TABLE _stage (
                asset_id   BIGINT,
                path       TEXT,
                filename   TEXT,
                ext        TEXT,
                size_bytes BIGINT,
                mtime      TIMESTAMPTZ,
                top_folder TEXT,
                sub_folder TEXT
            ) ON COMMIT DROP
        """)

        parsed = 0
        with cur.copy("""
            COPY _stage (asset_id, path, filename, ext, size_bytes, mtime, top_folder, sub_folder)
            FROM STDIN
        """) as copy:
            for full, size, mtime in walk_files():
                top, sub, fname, ext = parse_path(full)
                copy.write_row((None, full, fname, ext, size, mtime, top, sub))
                parsed += 1
                if parsed % 10000 == 0:
                    log.info(f'  스캔 중... {parsed:,}개')

        # 이미 적재된 경로 중복 제거 (재실행 멱등)
        cur.execute("""
            DELETE FROM _stage s
            USING asset_storage a
            WHERE a.realm = %s AND a.physical_path = s.path
        """, (REALM,))
        skipped = cur.rowcount

        cur.execute("UPDATE _stage SET asset_id = nextval('assets_id_seq')")

        cur.execute("""
            INSERT INTO assets (id, asset_type, filename, primary_ext, size_bytes, mtime)
            SELECT asset_id, 'source', filename, ext, size_bytes, mtime FROM _stage
        """)

        cur.execute("""
            INSERT INTO asset_storage
                (asset_id, realm, physical_path, top_folder, sub_folder, scan_run_id)
            SELECT asset_id, %s, path, top_folder, sub_folder, %s FROM _stage
        """, (REALM, run_id))
        inserted = cur.rowcount

        cur.execute("""
            INSERT INTO asset_tags_legacy (asset_id, namespace, value, source)
            SELECT asset_id, 'project', top_folder, 'path_inference'
            FROM _stage WHERE top_folder IS NOT NULL
            ON CONFLICT DO NOTHING
        """)

        cur.execute("""
            UPDATE scan_runs
            SET finished_at = now(),
                total_files = (SELECT COUNT(*)                    FROM _stage),
                total_bytes = (SELECT COALESCE(SUM(size_bytes),0) FROM _stage)
            WHERE id = %s
        """, (run_id,))

    conn.commit()
    elapsed = time.time() - t0
    log.info(f'완료 | parsed={parsed:,} inserted={inserted:,} skipped={skipped:,} ({elapsed:.1f}s)')
    return {'parsed': parsed, 'inserted': inserted, 'skipped': skipped}


def verify(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(a.size_bytes),0)/1e9
            FROM assets a JOIN asset_storage s ON s.asset_id = a.id
            WHERE s.realm = %s
        """, (REALM,))
        cnt, gb = cur.fetchone()
        log.info(f'검증 | poc_sample {cnt:,}개 / {gb:.2f} GB')

        cur.execute("""
            SELECT s.top_folder, COUNT(*), SUM(a.size_bytes)/1e9
            FROM asset_storage s JOIN assets a ON a.id = s.asset_id
            WHERE s.realm = %s
            GROUP BY s.top_folder ORDER BY 3 DESC LIMIT 15
        """, (REALM,))
        log.info('폴더별 TOP 15 (GB):')
        for row in cur.fetchall():
            log.info(f'  {str(row[0]):<45} {row[1]:>7,}개  {row[2]:>8.2f} GB')


def main():
    if not os.path.isdir(POC_ROOT):
        sys.exit(f'POC_ROOT 없음: {POC_ROOT}')
    with psycopg.connect(DB_DSN) as conn:
        ingest(conn)
        verify(conn)


if __name__ == '__main__':
    main()
