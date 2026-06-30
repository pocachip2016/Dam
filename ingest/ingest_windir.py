#!/usr/bin/env python3
"""
NFS 빠른 스캔 — Windows PowerShell Get-ChildItem 사용 (WSL2 9P 병목 우회)

os.walk(SMB over WSL2 9P) 대비 약 20배 빠름.
파일 복사 없이 NAS UNC 경로를 직접 열거 → Linux 마운트 경로로 변환 → PC-B DB 적재.

실행:
  DAM_REALM=designfs1_mirror \
  DAM_DSN='postgresql://dam:dam@222.112.179.161:15432/dam' \
  .venv/bin/python ingest/ingest_windir.py
"""
import csv, datetime, io, logging, os, subprocess, sys, time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

try:
    import psycopg
except ImportError:
    sys.exit('psycopg 미설치. 실행: pip install psycopg[binary]')

DAM_DSN    = os.environ.get('DAM_DSN',    'postgresql://dam:dam@222.112.179.161:15432/dam')
REALM      = os.environ.get('DAM_REALM',  'designfs1_mirror')

NAS_UNC    = r'\\designfs.ktalpha.com\DESIGNFS1\dam_dev\11.NEXT_UI_2022_10월오픈'
LINUX_ROOT = '/mnt/designfs1/dam_dev/11.NEXT_UI_2022_10월오픈'
UNC_PREFIX = r'\\designfs.ktalpha.com\DESIGNFS1'
LINUX_MNT  = '/mnt/designfs1'

PS_EXE = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'

SKIP_PREFIXES = ('._', '~$', '_')
SKIP_NAMES    = frozenset({'Thumbs.db', '.DS_Store', 'desktop.ini'})


def unc_to_linux(win_path: str) -> str:
    p = win_path.replace('\\', '/')
    prefix = UNC_PREFIX.replace('\\', '/')
    if p.startswith(prefix):
        return LINUX_MNT + p[len(prefix):]
    return p


def parse_path(full_path: str):
    root = LINUX_ROOT.rstrip('/')
    rel  = full_path[len(root) + 1:] if full_path.startswith(root + '/') else full_path
    parts = rel.split('/')
    fname = parts[-1]
    top   = parts[0] if len(parts) >= 2 else None
    sub   = parts[1] if len(parts) >= 3 else None
    _, ext = os.path.splitext(fname.lower())
    return top, sub, fname, ext or None


def ps_files():
    """PowerShell로 UNC 경로 파일 목록+메타데이터 수집 (Windows 네이티브 SMB)"""
    ps_cmd = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        f"Get-ChildItem -LiteralPath '{NAS_UNC}' -Recurse -File -ErrorAction SilentlyContinue | "
        r"Select-Object FullName, Length, "
        r"@{N='Mtime';E={[DateTimeOffset]::new($_.LastWriteTimeUtc,[TimeSpan]::Zero).ToUnixTimeSeconds()}} | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    log.info(f'PowerShell Get-ChildItem 시작: {NAS_UNC}')
    t0 = time.time()
    proc = subprocess.Popen(
        [PS_EXE, '-NoProfile', '-NonInteractive', '-Command', ps_cmd],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout_b, stderr_b = proc.communicate()
    elapsed = time.time() - t0
    log.info(f'PowerShell 완료: {elapsed:.0f}s  returncode={proc.returncode}')
    if stderr_b:
        log.warning(f'PS stderr: {stderr_b.decode("utf-8", errors="replace")[:400]}')

    raw = stdout_b.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(raw))
    count = 0
    for row in reader:
        try:
            win_path = row.get('FullName', '').strip('"')
            fname = win_path.replace('\\', '/').split('/')[-1]
            if fname in SKIP_NAMES or any(fname.startswith(p) for p in SKIP_PREFIXES):
                continue
            linux_path = unc_to_linux(win_path)
            size = int(row.get('Length', 0) or 0)
            mtime_ts = int(row.get('Mtime', 0) or 0)
            mtime = datetime.datetime.fromtimestamp(mtime_ts, tz=datetime.timezone.utc)
            yield linux_path, size, mtime
            count += 1
            if count % 10000 == 0:
                log.info(f'  파싱 중... {count:,}개')
        except Exception as e:
            log.debug(f'행 파싱 오류: {e} | {row}')


def ingest(conn) -> dict:
    log.info(f'빠른 NFS 스캔-적재 시작: realm={REALM}')
    t0 = time.time()

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO scan_runs (realm, source_root, notes)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id
        """, (REALM, LINUX_ROOT, '{"method": "windir_ps", "phase": "nfs-poc.6"}'))
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
            for full, size, mtime in ps_files():
                top, sub, fname, ext = parse_path(full)
                copy.write_row((None, full, fname, ext, size, mtime, top, sub))
                parsed += 1
                if parsed % 10000 == 0:
                    log.info(f'  COPY 중... {parsed:,}개')

        log.info(f'COPY 완료: {parsed:,}개')

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
                total_files = (SELECT COUNT(*) FROM _stage),
                total_bytes = (SELECT COALESCE(SUM(size_bytes), 0) FROM _stage)
            WHERE id = %s
        """, (run_id,))

    conn.commit()
    elapsed = time.time() - t0
    log.info(f'완료 | parsed={parsed:,} inserted={inserted:,} skipped={skipped:,} ({elapsed:.1f}s)')
    return {'parsed': parsed, 'inserted': inserted, 'skipped': skipped}


def verify(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(a.size_bytes), 0) / 1e9
            FROM assets a JOIN asset_storage s ON s.asset_id = a.id
            WHERE s.realm = %s
        """, (REALM,))
        cnt, gb = cur.fetchone()
        log.info(f'검증 | {REALM} {cnt:,}개 / {gb:.2f} GB')


def main():
    with psycopg.connect(DAM_DSN) as conn:
        ingest(conn)
        verify(conn)


if __name__ == '__main__':
    main()
