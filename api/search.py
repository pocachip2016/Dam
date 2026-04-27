#!/usr/bin/env python3
"""Phase 2 유사 이미지 검색 API

FastAPI 기반. 현재 구현:
  - GET /search?q=<파일명>&ext=.jpg&realm=poc_sample&limit=50  메타/파일명 검색
  - GET /similar/<asset_id>?limit=20                           CLIP 유사도 검색 (임베딩 있을 때만)
  - GET /asset/<asset_id>                                      단일 자산 상세
  - GET /thumb/<asset_id>                                      썸네일 이미지 파일 서빙
  - GET /stats                                                 realm별 집계

설치:
  pip install fastapi uvicorn psycopg[binary]

실행:
  python api/search.py
  또는
  uvicorn api.search:app --host 0.0.0.0 --port 18000 --reload
"""

import os, sys, logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import FileResponse, JSONResponse
    import uvicorn
except ImportError:
    sys.exit('FastAPI 미설치. 실행: pip install fastapi uvicorn')

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit('psycopg 미설치. 실행: pip install psycopg[binary]')

DB_DSN = os.environ.get('DAM_DSN', 'postgresql://dam:dam@localhost:15432/dam')
app    = FastAPI(title='Dam Search API', version='0.2.0')


def get_conn():
    return psycopg.connect(DB_DSN, row_factory=dict_row)


# ---------------------------------------------------------------------------
# GET /search
# ---------------------------------------------------------------------------
@app.get('/search')
def search(
    q:     Optional[str]  = Query(None,  description='파일명 검색 (trigram ILIKE)'),
    ext:   Optional[str]  = Query(None,  description='확장자 필터, 예: .jpg'),
    realm: str            = Query('poc_sample'),
    top:   Optional[str]  = Query(None,  description='top_folder 필터'),
    limit: int            = Query(50, ge=1, le=500),
    offset: int           = Query(0,  ge=0),
):
    filters = ['s.realm = %(realm)s']
    params: dict = {'realm': realm, 'limit': limit, 'offset': offset}

    if q:
        filters.append("a.filename ILIKE %(q)s")
        params['q'] = f'%{q}%'
    if ext:
        filters.append("a.primary_ext = %(ext)s")
        params['ext'] = ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
    if top:
        filters.append("s.top_folder = %(top)s")
        params['top'] = top

    where = ' AND '.join(filters)
    sql = f"""
        SELECT a.id, a.filename, a.primary_ext, a.size_bytes, a.mtime,
               a.width, a.height, a.thumbnail_path,
               s.physical_path, s.top_folder, s.sub_folder, s.realm
        FROM assets a
        JOIN asset_storage s ON s.asset_id = a.id
        WHERE {where}
        ORDER BY a.id DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.execute(f"SELECT COUNT(*) AS cnt FROM assets a JOIN asset_storage s ON s.asset_id=a.id WHERE {where}",
                        {k: v for k, v in params.items() if k not in ('limit', 'offset')})
            total = cur.fetchone()['cnt']

    return {'total': total, 'limit': limit, 'offset': offset, 'results': rows}


# ---------------------------------------------------------------------------
# GET /asset/<id>
# ---------------------------------------------------------------------------
@app.get('/asset/{asset_id}')
def get_asset(asset_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.id, a.filename, a.primary_ext, a.size_bytes, a.mtime,
                       a.sha256, a.width, a.height, a.thumbnail_path, a.ai_metadata,
                       a.asset_type, a.created_at
                FROM assets a WHERE a.id = %s
            """, (asset_id,))
            asset = cur.fetchone()
            if not asset:
                raise HTTPException(404, f'asset {asset_id} 없음')

            cur.execute("""
                SELECT realm, physical_path, top_folder, sub_folder, is_authoritative
                FROM asset_storage WHERE asset_id = %s
            """, (asset_id,))
            asset['storage'] = cur.fetchall()

            cur.execute("""
                SELECT namespace, value, source, confidence
                FROM asset_tags WHERE asset_id = %s
            """, (asset_id,))
            asset['tags'] = cur.fetchall()

    return asset


# ---------------------------------------------------------------------------
# GET /similar/<id>  — CLIP 유사도 (임베딩 필요)
# ---------------------------------------------------------------------------
@app.get('/similar/{asset_id}')
def similar(asset_id: int, limit: int = Query(20, ge=1, le=100), realm: str = 'poc_sample'):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT vector FROM embeddings
                WHERE asset_id = %s AND model_name = 'clip-vit-b32'
            """, (asset_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, f'asset {asset_id}의 임베딩 없음 (clip_worker.py 실행 필요)')

            cur.execute("""
                SELECT e.asset_id,
                       1 - (e.vector <=> %(vec)s::vector) AS similarity,
                       a.filename, a.primary_ext, a.thumbnail_path, s.physical_path
                FROM embeddings e
                JOIN assets a ON a.id = e.asset_id
                JOIN asset_storage s ON s.asset_id = e.asset_id AND s.realm = %(realm)s
                WHERE e.model_name = 'clip-vit-b32'
                  AND e.asset_id <> %(id)s
                ORDER BY e.vector <=> %(vec)s::vector
                LIMIT %(limit)s
            """, {'vec': row['vector'], 'id': asset_id, 'realm': realm, 'limit': limit})
            results = cur.fetchall()

    return {'asset_id': asset_id, 'results': results}


# ---------------------------------------------------------------------------
# GET /thumb/<id>  — 썸네일 파일 서빙
# ---------------------------------------------------------------------------
@app.get('/thumb/{asset_id}')
def thumb(asset_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT thumbnail_path FROM assets WHERE id = %s", (asset_id,))
            row = cur.fetchone()

    if not row or not row['thumbnail_path']:
        raise HTTPException(404, '썸네일 없음')
    path = row['thumbnail_path']
    if not os.path.isfile(path):
        raise HTTPException(404, f'썸네일 파일 없음: {path}')
    return FileResponse(path, media_type='image/jpeg')


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------
@app.get('/stats')
def stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.realm,
                       COUNT(*)                       AS files,
                       SUM(a.size_bytes)/1e9          AS gb,
                       COUNT(a.thumbnail_path)        AS thumbs,
                       COUNT(e.asset_id)              AS embedded
                FROM asset_storage s
                JOIN assets a ON a.id = s.asset_id
                LEFT JOIN embeddings e ON e.asset_id = s.asset_id AND e.model_name = 'clip-vit-b32'
                GROUP BY s.realm ORDER BY gb DESC
            """)
            by_realm = cur.fetchall()

            cur.execute("""
                SELECT a.primary_ext, COUNT(*), SUM(a.size_bytes)/1e9 AS gb
                FROM assets a
                JOIN asset_storage s ON s.asset_id = a.id
                WHERE s.realm = 'poc_sample'
                GROUP BY a.primary_ext ORDER BY gb DESC
            """)
            by_ext = cur.fetchall()

    return {'by_realm': by_realm, 'poc_sample_by_ext': by_ext}


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=18000, reload=False)
