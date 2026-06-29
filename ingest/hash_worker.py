#!/usr/bin/env python3
"""Phase 1.4 SHA-256 해시 워커 → duplicate_of 엣지 생성

실행 시점: Phase 3 직전 (NAS 파일이 로컬에서 접근 가능할 때)

설치:
  pip install psycopg[binary]

실행 예시:
  # 전체 (Phase 3 본실행)
  DAM_LOCAL_PREFIX=/mnt/designfs python ingest/hash_worker.py

  # 특정 탑폴더만 (테스트)
  DAM_TOP_FOLDER="11.NEXT_UI_2022_10월오픈" DAM_LOCAL_PREFIX=/mnt/designfs python ingest/hash_worker.py

환경변수:
  DAM_DSN          DB 연결 문자열 (기본: postgresql://dam:dam@localhost:15432/dam)
  DAM_UNC_PREFIX   DB에 저장된 UNC 접두어 (기본: \\\\designfs.ktalpha.com\\DESIGNFS)
  DAM_LOCAL_PREFIX 로컬 마운트 경로   (기본: /mnt/designfs)
  DAM_WORKERS      병렬 스레드 수     (기본: 4)
  DAM_BATCH_SIZE   DB 배치 크기       (기본: 500)
  DAM_TOP_FOLDER   특정 탑폴더만 처리 (기본: 전체)

동작:
  1. sha256 IS NULL인 source 파일을 BATCH_SIZE씩 조회
  2. WORKERS 스레드로 파일 스트리밍 SHA-256 계산 (4MB 청크)
  3. 성공 → sha256 갱신 / 접근 실패 → 'ERROR' 마킹 (재실행 시 스킵)
  4. 전체 완료 후 중복 그룹 탐지 → asset_edges(duplicate_of) 삽입
"""

import hashlib
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import PurePosixPath

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

try:
    import psycopg
except ImportError:
    sys.exit('psycopg 미설치. 실행: pip install psycopg[binary]')

DB_DSN       = os.environ.get('DAM_DSN',          'postgresql://dam:dam@localhost:15432/dam')
UNC_PREFIX   = os.environ.get('DAM_UNC_PREFIX',   r'\\designfs.ktalpha.com\DESIGNFS')
LOCAL_PREFIX = os.environ.get('DAM_LOCAL_PREFIX',  '/mnt/designfs')
WORKERS      = int(os.environ.get('DAM_WORKERS',   '4'))
BATCH_SIZE   = int(os.environ.get('DAM_BATCH_SIZE', '500'))
TOP_FOLDER   = os.environ.get('DAM_TOP_FOLDER',   '')
DAM_REALM    = os.environ.get('DAM_REALM',        '')

CHUNK_BYTES = 4 * 1024 * 1024  # 4 MB


def unc_to_local(unc_path: str) -> str:
    """\\server\share\foo\bar → /mnt/local/foo/bar"""
    fwd = unc_path.replace('\\', '/')
    prefix = UNC_PREFIX.replace('\\', '/')
    if fwd.startswith(prefix):
        rel = fwd[len(prefix):].lstrip('/')
        return str(PurePosixPath(LOCAL_PREFIX) / rel)
    return unc_path


def sha256_file(local_path: str):
    """스트리밍 SHA-256. 반환: 64자 hex 또는 None(접근 실패)"""
    try:
        h = hashlib.sha256()
        with open(local_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_BYTES)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError as e:
        log.warning('접근 실패: %s — %s', local_path, e)
        return None


def fetch_batch(conn):
    """미해시 파일 배치 반환: [(asset_id, local_path), ...]"""
    top_cond   = "AND s.top_folder = %(top)s" if TOP_FOLDER else ""
    realm_cond = "AND s.realm = %(realm)s"    if DAM_REALM  else ""
    params = {'limit': BATCH_SIZE, 'top': TOP_FOLDER or None, 'realm': DAM_REALM or None}
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT a.id, s.physical_path
            FROM   assets a
            JOIN   asset_storage s ON s.asset_id = a.id
            WHERE  a.asset_type = 'source'
              AND  a.sha256 IS NULL
              {realm_cond}
              {top_cond}
            ORDER BY a.id
            LIMIT %(limit)s
        """, params)
        rows = cur.fetchall()
    return [(aid, unc_to_local(path)) for aid, path in rows]


def hash_batch(rows):
    """병렬 해시 계산. 반환: [(asset_id, sha256_or_None), ...]"""
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(sha256_file, path): aid for aid, path in rows}
        for fut in as_completed(futures):
            results.append((futures[fut], fut.result()))
    return results


def write_hashes(conn, results):
    """해시 결과 DB 반영. 반환: (updated, failed)"""
    ok   = [(h, aid) for aid, h in results if h is not None]
    fail = [(aid,)   for aid, h in results if h is None]
    with conn.cursor() as cur:
        if ok:
            cur.executemany("UPDATE assets SET sha256 = %s WHERE id = %s", ok)
        if fail:
            # 'ERROR' 마킹: 재실행 시 sha256 IS NULL 조건에 걸리지 않아 스킵됨
            cur.executemany("UPDATE assets SET sha256 = 'ERROR' WHERE id = %s", fail)
    conn.commit()
    return len(ok), len(fail)


def build_duplicate_edges(conn) -> int:
    """동일 sha256 그룹 → duplicate_of 엣지 삽입. 반환: 삽입 행수"""
    log.info('중복 엣지 생성 중...')
    with conn.cursor() as cur:
        cur.execute("""
            WITH ranked AS (
                SELECT id,
                       sha256,
                       MIN(id) OVER (PARTITION BY sha256) AS canonical_id,
                       COUNT(*) OVER (PARTITION BY sha256) AS cnt
                FROM   assets
                WHERE  sha256 IS NOT NULL
                  AND  sha256 <> 'ERROR'
                  AND  asset_type = 'source'
            )
            INSERT INTO asset_edges
                (parent_id, child_id, relation, confidence, metadata)
            SELECT canonical_id,
                   id,
                   'duplicate_of',
                   1.0,
                   jsonb_build_object('sha256', sha256)
            FROM   ranked
            WHERE  cnt > 1
              AND  id <> canonical_id
            ON CONFLICT DO NOTHING
        """)
        count = cur.rowcount
    conn.commit()
    return count


def count_pending(conn) -> int:
    top_cond = "AND s.top_folder = %(top)s" if TOP_FOLDER else ""
    params = {'top': TOP_FOLDER or None}
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT COUNT(*)
            FROM   assets a
            JOIN   asset_storage s ON s.asset_id = a.id
            WHERE  a.asset_type = 'source'
              AND  a.sha256 IS NULL
              {top_cond}
        """, params)
        return cur.fetchone()[0]


def main():
    log.info('해시 워커 시작 | workers=%d batch=%d', WORKERS, BATCH_SIZE)
    log.info('경로 변환: %r → %r', UNC_PREFIX, LOCAL_PREFIX)
    if TOP_FOLDER:
        log.info('필터: top_folder = %r', TOP_FOLDER)

    t0            = time.time()
    total_updated = 0
    total_failed  = 0
    processed     = 0
    dup_edges     = 0

    with psycopg.connect(DB_DSN) as conn:
        total = count_pending(conn)
        log.info('미해시 파일: %d개', total)

        while True:
            rows = fetch_batch(conn)
            if not rows:
                break

            results              = hash_batch(rows)
            updated, failed      = write_hashes(conn, results)
            total_updated       += updated
            total_failed        += failed
            processed           += len(rows)

            elapsed = time.time() - t0
            pct     = processed / total * 100 if total else 100
            rate    = processed / elapsed if elapsed > 0 else 0
            eta_min = (total - processed) / rate / 60 if rate > 0 else 0
            log.info(
                '진행 %d/%d (%.1f%%) | 성공=%d 실패=%d | %.0f개/s | ETA %.1f분',
                processed, total, pct, total_updated, total_failed, rate, eta_min,
            )

        dup_edges = build_duplicate_edges(conn)
        log.info('중복 엣지: %d개 삽입', dup_edges)

    elapsed = time.time() - t0
    log.info(
        '전체 완료 | updated=%d failed=%d duplicate_edges=%d | 소요=%.1f분',
        total_updated, total_failed, dup_edges, elapsed / 60,
    )


if __name__ == '__main__':
    main()
