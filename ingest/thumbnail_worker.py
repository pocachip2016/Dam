#!/usr/bin/env python3
"""Phase 2 썸네일 생성 워커

poc_sample의 이미지(jpg/png/gif/webp)를 읽어 512x512 max 썸네일 생성.
썸네일은 /home/pocachip/dam_data/thumbnails/<asset_id>.jpg 로 저장.
assets.thumbnail_path 컬럼을 업데이트하고
asset_edges(parent=원본, child=썸네일, relation='derived_from') 엣지를 추가.

사전조건:
  - 002_embeddings.sql 적용 완료 (thumbnail_path 컬럼 존재)
  - poc_sample 적재 완료 (ingest_local.py 실행 후)

설치:
  pip install psycopg[binary] Pillow

실행:
  python ingest/thumbnail_worker.py
  THUMB_DIR=/home/pocachip/dam_data/thumbnails WORKERS=4 python ingest/thumbnail_worker.py
"""

import os, sys, time, logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

try:
    import psycopg
except ImportError:
    sys.exit('psycopg 미설치. 실행: pip install psycopg[binary]')

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    sys.exit('Pillow 미설치. 실행: pip install Pillow')

DB_DSN    = os.environ.get('DAM_DSN',    'postgresql://dam:dam@localhost:15432/dam')
THUMB_DIR = os.environ.get('THUMB_DIR',  '/home/pocachip/dam_data/thumbnails')
REALM     = 'poc_sample'
THUMB_MAX = 512          # 장축 최대 픽셀
WORKERS   = int(os.environ.get('WORKERS', '2'))
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}


def make_thumb(args) -> dict:
    """단일 파일 썸네일 생성. ProcessPoolExecutor용."""
    asset_id, src_path, thumb_path = args
    try:
        with Image.open(src_path) as img:
            img = img.convert('RGB')
            img.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            img.save(thumb_path, 'JPEG', quality=85, optimize=True)
        return {'asset_id': asset_id, 'thumb_path': thumb_path, 'ok': True}
    except (UnidentifiedImageError, OSError, Exception) as e:
        return {'asset_id': asset_id, 'thumb_path': thumb_path, 'ok': False, 'err': str(e)}


def fetch_pending(conn) -> list:
    """썸네일 미생성 이미지 자산 목록 반환"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT a.id, s.physical_path
            FROM assets a
            JOIN asset_storage s ON s.asset_id = a.id
            WHERE s.realm = %s
              AND a.asset_type = 'source'
              AND a.thumbnail_path IS NULL
              AND a.primary_ext = ANY(%s)
            ORDER BY a.id
        """, (REALM, list(IMAGE_EXTS)))
        return cur.fetchall()


def register_thumb(conn, asset_id: int, thumb_path: str):
    """DB에 썸네일 경로 갱신"""
    with conn.cursor() as cur:
        cur.execute("UPDATE assets SET thumbnail_path = %s WHERE id = %s",
                    (thumb_path, asset_id))
    conn.commit()


def main():
    os.makedirs(THUMB_DIR, exist_ok=True)
    log.info(f'썸네일 디렉토리: {THUMB_DIR}')

    with psycopg.connect(DB_DSN) as conn:
        pending = fetch_pending(conn)
        log.info(f'처리 대상: {len(pending):,}개')
        if not pending:
            log.info('처리할 파일 없음 (모두 완료 또는 poc_sample 미적재)')
            return

        tasks = []
        for asset_id, src_path in pending:
            sub_dir = str(asset_id // 1000).zfill(4)
            thumb_path = os.path.join(THUMB_DIR, sub_dir, f'{asset_id}.jpg')
            tasks.append((asset_id, src_path, thumb_path))

        ok = err = 0
        t0 = time.time()
        batch = []

        with ProcessPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(make_thumb, t): t for t in tasks}
            for future in as_completed(futures):
                res = future.result()
                if res['ok']:
                    batch.append((res['asset_id'], res['thumb_path']))
                    ok += 1
                else:
                    log.debug(f"오류 asset_id={res['asset_id']}: {res.get('err')}")
                    err += 1

                if len(batch) >= 200:
                    with conn.cursor() as cur:
                        cur.executemany(
                            "UPDATE assets SET thumbnail_path = %s WHERE id = %s",
                            [(tp, aid) for aid, tp in batch]
                        )
                    conn.commit()
                    batch.clear()

                if (ok + err) % 1000 == 0:
                    elapsed = time.time() - t0
                    log.info(f'  진행 {ok+err:,}/{len(tasks):,} | ok={ok:,} err={err:,} ({elapsed:.0f}s)')

        if batch:
            with conn.cursor() as cur:
                cur.executemany(
                    "UPDATE assets SET thumbnail_path = %s WHERE id = %s",
                    [(tp, aid) for aid, tp in batch]
                )
            conn.commit()

        elapsed = time.time() - t0
        log.info(f'완료 | ok={ok:,} err={err:,} ({elapsed:.1f}s)')

        # 결과 요약
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM assets a
                JOIN asset_storage s ON s.asset_id = a.id
                WHERE s.realm = %s AND a.thumbnail_path IS NOT NULL
            """, (REALM,))
            done = cur.fetchone()[0]
            log.info(f'poc_sample 썸네일 완료 누적: {done:,}개')


if __name__ == '__main__':
    main()
