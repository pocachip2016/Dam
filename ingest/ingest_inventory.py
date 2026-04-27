#!/usr/bin/env python3
"""Phase 1 UTF-16 인벤토리 파서 → PostgreSQL 전량 적재

설치:
  pip install psycopg[binary]

실행 (WSL2):
  python ingest/ingest_inventory.py
  DAM_DSN="postgresql://dam:dam@localhost:15432/dam" python ingest/ingest_inventory.py

입력: /mnt/d/dam_analysis/scan_logs/inv_*.txt
  - 인코딩: UTF-16 LE (BOM 포함)
  - 포맷: 탭 구분, 마지막 두 컬럼 = size_bytes  UNC_path
  - UNC 예: \\\\designfs.ktalpha.com\\DESIGNFS\\디자인파트\\00. 디자인파트_관리\\sub\\file.ai

출력 테이블: assets + asset_storage + asset_tags + scan_runs
재실행: (realm, physical_path) 이미 존재하면 스킵 — 멱등(idempotent)
"""

import os, sys, glob, time, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

try:
    import psycopg
except ImportError:
    sys.exit('psycopg 미설치. 실행: pip install psycopg[binary]')

SCAN_DIR    = os.environ.get('DAM_SCAN_DIR', '/mnt/d/dam_analysis/scan_logs')
DB_DSN      = os.environ.get('DAM_DSN',      'postgresql://dam:dam@localhost:15432/dam')
REALM       = 'designfs'
SOURCE_ROOT = r'\\designfs.ktalpha.com\DESIGNFS\디자인파트'


def parse_path(path: str) -> tuple:
    """UNC 경로 → (top_folder, sub_folder, filename, ext)"""
    parts = path.split('\\')
    try:
        idx = parts.index('디자인파트')
        rel = parts[idx + 1:]
    except ValueError:
        rel = parts
    if not rel:
        return None, None, path, None
    top      = rel[0] if len(rel) >= 2 else None
    sub      = rel[1] if len(rel) >= 3 else None
    filename = rel[-1]
    _, ext   = os.path.splitext(filename.lower())
    return top, sub, filename, ext or None


def ingest_file(conn, inv_path: str) -> dict:
    top_name = os.path.basename(inv_path).replace('inv_', '').replace('.txt', '')
    log.info(f'[{top_name}] 시작: {inv_path}')
    t0 = time.time()

    with conn.cursor() as cur:
        # 1) scan_runs 감사 행 생성
        cur.execute("""
            INSERT INTO scan_runs (realm, source_root, notes)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id
        """, (REALM, SOURCE_ROOT,
              f'{{"top": "{top_name}", "file": "{os.path.basename(inv_path)}"}}'))
        run_id = cur.fetchone()[0]

        # 2) 세션 한정 스테이징 테이블
        cur.execute("""
            CREATE TEMP TABLE _stage (
                asset_id   BIGINT,
                path       TEXT,
                filename   TEXT,
                ext        TEXT,
                size_bytes BIGINT,
                top_folder TEXT,
                sub_folder TEXT
            ) ON COMMIT DROP
        """)

        # 3) UTF-16 파싱 → COPY INTO staging
        parsed = 0
        errors = 0
        with cur.copy("""
            COPY _stage (asset_id, path, filename, ext, size_bytes, top_folder, sub_folder)
            FROM STDIN
        """) as copy:
            with open(inv_path, encoding='utf-16') as f:
                for line in f:
                    cols = line.rstrip('\r\n').split('\t')
                    if len(cols) < 2:
                        continue
                    try:
                        size = int(cols[-2].strip())
                    except ValueError:
                        errors += 1
                        continue
                    path = cols[-1].strip()
                    if not path:
                        continue
                    top, sub, fname, ext = parse_path(path)
                    copy.write_row((None, path, fname, ext, size, top, sub))
                    parsed += 1

        if errors:
            log.warning(f'[{top_name}] 파싱 오류 {errors}행 무시')

        # 4) 기존 경로 중복 제거 (재실행 시 멱등 보장)
        cur.execute("""
            DELETE FROM _stage s
            USING asset_storage a
            WHERE a.realm = %s AND a.physical_path = s.path
        """, (REALM,))
        skipped = cur.rowcount

        # 5) asset_id 시퀀스 일괄 할당
        cur.execute("UPDATE _stage SET asset_id = nextval('assets_id_seq')")

        # 6) assets 삽입
        cur.execute("""
            INSERT INTO assets (id, asset_type, filename, primary_ext, size_bytes)
            SELECT asset_id, 'source', filename, ext, size_bytes FROM _stage
        """)

        # 7) asset_storage 삽입
        cur.execute("""
            INSERT INTO asset_storage
                (asset_id, realm, physical_path, top_folder, sub_folder, scan_run_id)
            SELECT asset_id, %s, path, top_folder, sub_folder, %s FROM _stage
        """, (REALM, run_id))
        inserted = cur.rowcount

        # 8) project 태그 (폴더명 기반)
        cur.execute("""
            INSERT INTO asset_tags (asset_id, namespace, value, source)
            SELECT asset_id, 'project', top_folder, 'path_inference'
            FROM _stage WHERE top_folder IS NOT NULL
            ON CONFLICT DO NOTHING
        """)

        # 9) scan_runs 마감
        cur.execute("""
            UPDATE scan_runs
            SET finished_at = now(),
                total_files = (SELECT COUNT(*)                    FROM _stage),
                total_bytes = (SELECT COALESCE(SUM(size_bytes),0) FROM _stage)
            WHERE id = %s
        """, (run_id,))

    conn.commit()
    elapsed = time.time() - t0
    log.info(
        f'[{top_name}] 완료 | parsed={parsed:,} inserted={inserted:,} '
        f'skipped={skipped:,} ({elapsed:.1f}s)'
    )
    return {'parsed': parsed, 'inserted': inserted, 'skipped': skipped}


def verify(conn):
    """적재 후 검증 요약 출력"""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), SUM(size_bytes)/1e12 FROM assets WHERE asset_type='source'")
        cnt, tb = cur.fetchone()
        log.info(f'검증 | 총 {cnt:,}개 / {tb:.2f} TB (source 자산)')

        cur.execute("""
            SELECT top_folder, COUNT(*), SUM(a.size_bytes)/1e9
            FROM asset_storage s JOIN assets a ON a.id=s.asset_id
            WHERE s.realm=%s
            GROUP BY top_folder ORDER BY 3 DESC LIMIT 10
        """, (REALM,))
        log.info('탑레벨 TOP 10 (GB):')
        for row in cur.fetchall():
            log.info(f'  {row[0]:<40} {row[1]:>8,}개  {row[2]:>8.2f} GB')


def main():
    files = sorted(glob.glob(os.path.join(SCAN_DIR, 'inv_*.txt')))
    if not files:
        sys.exit(f'inv_*.txt 없음: {SCAN_DIR}')
    log.info(f'인벤토리 {len(files)}개 발견 | DB: {DB_DSN}')

    totals = {'parsed': 0, 'inserted': 0, 'skipped': 0}
    with psycopg.connect(DB_DSN) as conn:
        for fp in files:
            r = ingest_file(conn, fp)
            for k in totals:
                totals[k] += r[k]
        verify(conn)

    log.info(
        f'전체 완료 | parsed={totals["parsed"]:,} '
        f'inserted={totals["inserted"]:,} skipped={totals["skipped"]:,}'
    )


if __name__ == '__main__':
    main()
