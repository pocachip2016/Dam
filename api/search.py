#!/usr/bin/env python3
"""Phase 2 유사 이미지 검색 API

FastAPI 기반. 현재 구현:
  - GET /search?q=<파일명>&ext=.jpg&realm=poc_sample&limit=50  메타/파일명 검색
  - GET /search_text?q=<텍스트>&model=clip-vit-b32&realm=poc_sample&limit=20
  - GET /similar/<asset_id>?model=clip-vit-b32&limit=20        CLIP 유사도 검색
  - GET /asset/<asset_id>                                      단일 자산 상세
  - GET /thumb/<asset_id>                                      썸네일 이미지 파일 서빙
  - GET /stats                                                 realm별 집계 (모델별 embedded 포함)

실행:
  DAM_DSN=... python -m api.search
  uvicorn api.search:app --host 127.0.0.1 --port 18000 --reload
"""

import os
import sys
import logging
import threading
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

try:
    from fastapi import Depends, FastAPI, HTTPException, Query
    from fastapi.responses import FileResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    sys.exit('FastAPI 미설치. 실행: pip install fastapi')

from api.auth import User, require_user, router as auth_router
from api.search_filters import build_filters
from api.tags import router as tags_router
from api.collections import router as collections_router
from api.mapping import router as mapping_router
from api.admin import router as admin_router
from api.ingest_poster import router as ingest_poster_router
from api.ingest_tmdb_image import router as ingest_tmdb_image_router

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit('psycopg 미설치. 실행: pip install psycopg[binary]')

DB_DSN = os.environ.get('DAM_DSN', 'postgresql://dam:dam@localhost:15432/dam')
MODEL_CACHE_DIR = os.environ.get('MODEL_CACHE_DIR',
    str(Path.home() / 'Work/Dam/dam_data/models'))

app = FastAPI(title='Dam Search API', version='0.4.0')

_static_dir = Path(__file__).parent / 'static'
if _static_dir.exists():
    app.mount('/static', StaticFiles(directory=str(_static_dir)), name='static')

cors_origins = os.getenv('DAM_CORS_ORIGINS', 'http://localhost:3001').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth_router)
app.include_router(tags_router)
app.include_router(collections_router)
app.include_router(mapping_router)
app.include_router(admin_router)
app.include_router(ingest_poster_router)
app.include_router(ingest_tmdb_image_router)

@app.get('/', include_in_schema=False)
def root():
    return RedirectResponse('/static/index.html')

# ---------------------------------------------------------------------------
# 텍스트 인코더 lazy singleton
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()
_models: dict = {}

SUPPORTED_MODELS = {'clip-vit-b32', 'cn-clip-vitb16'}


def _load_open_clip():
    import torch
    import open_clip
    os.environ.setdefault('HF_HUB_CACHE', MODEL_CACHE_DIR)
    os.environ.setdefault('TORCH_HOME', MODEL_CACHE_DIR)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model, _, _ = open_clip.create_model_and_transforms(
        'ViT-B-32', pretrained='laion2b_s34b_b79k')
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer('ViT-B-32')
    log.info(f'open_clip ViT-B/32 로드 완료 (device={device})')
    return model, tokenizer, device


def _load_cn_clip():
    import torch
    import cn_clip.clip as clip
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model, _ = clip.load_from_name('ViT-B-16', device=device,
                                   download_root=MODEL_CACHE_DIR)
    model.eval()
    log.info(f'cn_clip ViT-B/16 로드 완료 (device={device})')
    return model, None, device


def get_model(model_name: str):
    with _model_lock:
        if model_name not in _models:
            if model_name == 'clip-vit-b32':
                _models[model_name] = _load_open_clip()
            elif model_name == 'cn-clip-vitb16':
                _models[model_name] = _load_cn_clip()
            else:
                raise ValueError(f'지원하지 않는 모델: {model_name}')
    return _models[model_name]


def encode_text(query: str, model_name: str) -> list:
    import torch
    model, tokenizer, device = get_model(model_name)
    with torch.no_grad():
        if model_name == 'clip-vit-b32':
            tokens = tokenizer([query]).to(device)
            feat = model.encode_text(tokens)
        else:  # cn-clip-vitb16
            import cn_clip.clip as clip
            tokens = clip.tokenize([query]).to(device)
            feat = model.encode_text(tokens)
        feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.cpu().float().numpy()[0].tolist()


# ---------------------------------------------------------------------------
# DB 연결
# ---------------------------------------------------------------------------
def get_conn():
    return psycopg.connect(DB_DSN, row_factory=dict_row)


# ---------------------------------------------------------------------------
# GET /search  — 파일명/메타 검색
# ---------------------------------------------------------------------------
@app.get('/search')
def search(
    q:      Optional[str] = Query(None,  description='파일명 검색 (trigram ILIKE)'),
    ext:    Optional[str] = Query(None,  description='확장자 필터, 예: .jpg'),
    realm:  str           = Query('poc_sample'),
    top:    Optional[str] = Query(None,  description='top_folder 필터'),
    sub:    Optional[str] = Query(None,  description='sub_folder 필터'),
    limit:  int           = Query(50, ge=1, le=500),
    offset: int           = Query(0,  ge=0),
    user:   User          = Depends(require_user('viewer')),
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
    if sub:
        filters.append("s.sub_folder = %(sub)s")
        params['sub'] = sub

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
            cnt_params = {k: v for k, v in params.items() if k not in ('limit', 'offset')}
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM assets a JOIN asset_storage s ON s.asset_id=a.id WHERE {where}",
                cnt_params)
            total = cur.fetchone()['cnt']

    return {'total': total, 'limit': limit, 'offset': offset, 'results': rows}


# ---------------------------------------------------------------------------
# GET /search_text  — 텍스트 → CLIP 임베딩 → 유사 이미지 검색
# ---------------------------------------------------------------------------
@app.get('/search_text')
def search_text(
    q:          str            = Query('',   description='검색 텍스트 (비워도 필터만으로 검색 가능)'),
    model:      str            = Query('clip-vit-b32', description='clip-vit-b32 | cn-clip-vitb16'),
    realm:      str            = Query('poc_sample'),
    limit:      int            = Query(20, ge=1, le=100),
    ext:        Optional[str]  = Query(None, description='확장자 CSV: jpg,png'),
    folder:     Optional[str]  = Query(None, description='폴더 토큰 (GIN @>)'),
    role:       Optional[str]  = Query(None, description='role CSV: poster,banner'),
    year_from:  Optional[int]  = Query(None),
    year_to:    Optional[int]  = Query(None),
    size_min_mb: Optional[float] = Query(None),
    size_max_mb: Optional[float] = Query(None),
    mtime_from: Optional[str]  = Query(None, description='ISO date'),
    mtime_to:   Optional[str]  = Query(None, description='ISO date'),
    tag:          Optional[str]  = Query(None, description='태그 CSV (AND 조건)'),
    text_search:  Optional[str]  = Query(None, description='ocr_only | clip_only (기본: 둘 다)'),
    class_filter: Optional[str]  = Query(None, description='자산 분류 class (content/promotion/…)'),
    content_id:   Optional[int]  = Query(None, description='콘텐츠 ID — 해당 콘텐츠 매핑 자산만'),
    top_folder:   Optional[str]  = Query(None, description='최상위 폴더 (디자이너/카테고리)'),
    hide_draft:   bool           = Query(True,  description='draft+composition 자산 숨김 (기본: true)'),
    user:         User           = Depends(require_user('viewer')),
):
    filter_clauses, filter_params = build_filters({
        'ext': ext, 'folder': folder, 'role': role,
        'year_from': year_from, 'year_to': year_to,
        'size_min_mb': size_min_mb, 'size_max_mb': size_max_mb,
        'mtime_from': mtime_from, 'mtime_to': mtime_to,
        'tag': tag,
        'class_filter': class_filter,
        'content_id': content_id,
        'top_folder': top_folder,
        'hide_draft': hide_draft,
    })

    if q and text_search != 'ocr_only':
        # Vector (CLIP) search path
        if model not in SUPPORTED_MODELS:
            raise HTTPException(400, f'model은 {SUPPORTED_MODELS} 중 하나여야 합니다')
        try:
            vec = encode_text(q, model)
        except Exception as e:
            raise HTTPException(500, f'텍스트 인코딩 실패: {e}')
        vec_str = '[' + ','.join(map(str, vec)) + ']'

        extra_where = (' AND ' + ' AND '.join(filter_clauses)) if filter_clauses else ''
        params = {'vec': vec_str, 'model': model, 'realm': realm, 'limit': limit,
                  **filter_params}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT e.asset_id,
                           1 - (e.vector <=> %(vec)s::vector) AS similarity,
                           a.filename, a.primary_ext, a.size_bytes,
                           a.thumbnail_path, s.physical_path,
                           a.year_hint, a.role_hint,
                           ts_headline('simple', coalesce(a.ocr_text,''), plainto_tsquery('simple', %(q_plain)s),
                             'MaxFragments=1,MinWords=5,MaxWords=10') AS ocr_snippet
                    FROM embeddings e
                    JOIN assets a ON a.id = e.asset_id
                    JOIN asset_storage s ON s.asset_id = e.asset_id AND s.realm = %(realm)s
                    WHERE e.model_name = %(model)s{extra_where}
                    ORDER BY e.vector <=> %(vec)s::vector
                    LIMIT %(limit)s
                """, {**params, 'q_plain': q})
                results = cur.fetchall()

    elif q and text_search == 'ocr_only':
        # OCR full-text search only
        base_clauses = ['s.realm = %(realm)s', "a.ocr_tsv @@ plainto_tsquery('simple', %(q_plain)s)"] + filter_clauses
        where = ' AND '.join(base_clauses)
        params = {'realm': realm, 'limit': limit, 'q_plain': q, **filter_params}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT a.id AS asset_id,
                           ts_rank(a.ocr_tsv, plainto_tsquery('simple', %(q_plain)s)) AS similarity,
                           a.filename, a.primary_ext, a.size_bytes,
                           a.thumbnail_path, s.physical_path,
                           a.year_hint, a.role_hint,
                           ts_headline('simple', coalesce(a.ocr_text,''), plainto_tsquery('simple', %(q_plain)s),
                             'MaxFragments=1,MinWords=5,MaxWords=10') AS ocr_snippet
                    FROM assets a
                    JOIN asset_storage s ON s.asset_id = a.id
                    WHERE {where}
                    ORDER BY similarity DESC
                    LIMIT %(limit)s
                """, params)
                results = cur.fetchall()
    else:
        # Metadata-only filter path (no vector)
        base_clauses = ['s.realm = %(realm)s'] + filter_clauses
        where = ' AND '.join(base_clauses)
        params = {'realm': realm, 'limit': limit, **filter_params}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT a.id AS asset_id,
                           NULL::float AS similarity,
                           a.filename, a.primary_ext, a.size_bytes,
                           a.thumbnail_path, s.physical_path,
                           a.year_hint, a.role_hint
                    FROM assets a
                    JOIN asset_storage s ON s.asset_id = a.id
                    WHERE {where}
                    ORDER BY a.id DESC
                    LIMIT %(limit)s
                """, params)
                results = cur.fetchall()

    return {'query': q, 'model': model, 'results': results}


@app.get('/filename_search')
def filename_search(
    q:     str = Query(..., description='파일명 토큰 검색'),
    realm: str = Query('poc_sample'),
    limit: int = Query(20, ge=1, le=100),
    user:  User = Depends(require_user('viewer')),
):
    token = q.strip().lower()
    if not token:
        return {'query': q, 'results': []}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.id AS asset_id, a.filename, a.primary_ext,
                       a.size_bytes, a.thumbnail_path, s.physical_path
                FROM assets a
                JOIN asset_storage s ON s.asset_id = a.id
                WHERE s.realm = %(realm)s
                  AND a.filename_tokens @> %(tok)s
                ORDER BY a.id DESC
                LIMIT %(limit)s
            """, {'realm': realm, 'tok': [token], 'limit': limit})
            results = cur.fetchall()
    return {'query': q, 'results': results}


# ---------------------------------------------------------------------------
# GET /asset/<id>
# ---------------------------------------------------------------------------
@app.get('/asset/{asset_id}')
def get_asset(asset_id: int, user: User = Depends(require_user('viewer'))):
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

            # new normalized tags
            cur.execute("""
                SELECT at.tag_id, t.namespace, t.name, at.added_by, at.added_at
                FROM asset_tags at JOIN tags t ON t.id = at.tag_id
                WHERE at.asset_id = %s
            """, (asset_id,))
            asset['tags'] = cur.fetchall()
            # legacy path_inference tags
            cur.execute("""
                SELECT namespace, value, source, confidence
                FROM asset_tags_legacy WHERE asset_id = %s
            """, (asset_id,))
            asset['tags_legacy'] = cur.fetchall()

    return asset


# ---------------------------------------------------------------------------
# GET /similar/<id>  — CLIP 유사도 검색
# ---------------------------------------------------------------------------
@app.get('/similar/{asset_id}')
def similar(
    asset_id: int,
    model: str = Query('clip-vit-b32', description='clip-vit-b32 | cn-clip-vitb16'),
    limit: int = Query(20, ge=1, le=100),
    realm: str = Query('poc_sample'),
    user:  User = Depends(require_user('viewer')),
):
    if model not in SUPPORTED_MODELS:
        raise HTTPException(400, f'model은 {SUPPORTED_MODELS} 중 하나여야 합니다')

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT vector FROM embeddings
                WHERE asset_id = %s AND model_name = %s
            """, (asset_id, model))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404,
                    f'asset {asset_id}의 {model} 임베딩 없음 (clip_worker.py 실행 필요)')

            cur.execute("""
                SELECT e.asset_id,
                       1 - (e.vector <=> %(vec)s::vector) AS similarity,
                       a.filename, a.primary_ext, a.thumbnail_path, s.physical_path
                FROM embeddings e
                JOIN assets a ON a.id = e.asset_id
                JOIN asset_storage s ON s.asset_id = e.asset_id AND s.realm = %(realm)s
                WHERE e.model_name = %(model)s
                  AND e.asset_id <> %(id)s
                ORDER BY e.vector <=> %(vec)s::vector
                LIMIT %(limit)s
            """, {'vec': row['vector'], 'model': model, 'id': asset_id,
                  'realm': realm, 'limit': limit})
            results = cur.fetchall()

    return {'asset_id': asset_id, 'model': model, 'results': results}


# ---------------------------------------------------------------------------
# GET /thumb/<id>
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
# GET /folders  — folder tree (top_folder -> sub_folder)
# ---------------------------------------------------------------------------
_folders_user = Depends(require_user('viewer'))

@app.get('/folders')
def list_folders(
    realm: str = Query('poc_sample'),
    user:  User = _folders_user,
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.top_folder, s.sub_folder, COUNT(*) AS count
                FROM asset_storage s
                JOIN assets a ON a.id = s.asset_id
                WHERE s.realm = %(realm)s AND s.top_folder IS NOT NULL
                GROUP BY s.top_folder, s.sub_folder
                ORDER BY s.top_folder, s.sub_folder
            """, {'realm': realm})
            rows = cur.fetchall()

    nodes_dict = {}
    for row in rows:
        top = row['top_folder']
        sub = row['sub_folder']
        count = row['count']

        if top not in nodes_dict:
            nodes_dict[top] = {'name': top, 'count': 0, 'children': {}}

        if sub:
            if sub not in nodes_dict[top]['children']:
                nodes_dict[top]['children'][sub] = {'name': sub, 'count': 0}
            nodes_dict[top]['children'][sub]['count'] += count
            nodes_dict[top]['count'] += count
        else:
            nodes_dict[top]['count'] += count

    nodes = []
    for top_node in sorted(nodes_dict.values(), key=lambda x: x['name']):
        top_node['children'] = list(sorted(top_node['children'].values(), key=lambda x: x['name']))
        nodes.append(top_node)

    return {'realm': realm, 'nodes': nodes}


# ---------------------------------------------------------------------------
# GET /stats  — realm별 집계 + 모델별 embedded 카운트
# ---------------------------------------------------------------------------
@app.get('/stats')
def stats(user: User = Depends(require_user('viewer'))):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.realm,
                       COUNT(*)               AS files,
                       SUM(a.size_bytes)/1e9  AS gb,
                       COUNT(a.thumbnail_path) AS thumbs
                FROM asset_storage s
                JOIN assets a ON a.id = s.asset_id
                GROUP BY s.realm ORDER BY gb DESC
            """)
            realm_rows = {r['realm']: dict(r) for r in cur.fetchall()}

            cur.execute("""
                SELECT s.realm, e.model_name, COUNT(*) AS cnt
                FROM embeddings e
                JOIN asset_storage s ON s.asset_id = e.asset_id
                GROUP BY s.realm, e.model_name
            """)
            for row in cur.fetchall():
                realm_rows.setdefault(row['realm'], {}).setdefault(
                    'embedded', {})[row['model_name']] = row['cnt']

            for r in realm_rows.values():
                r.setdefault('embedded', {})

            cur.execute("""
                SELECT a.primary_ext, COUNT(*), SUM(a.size_bytes)/1e9 AS gb
                FROM assets a
                JOIN asset_storage s ON s.asset_id = a.id
                WHERE s.realm = 'poc_sample'
                GROUP BY a.primary_ext ORDER BY gb DESC
            """)
            by_ext = cur.fetchall()

    return {'by_realm': list(realm_rows.values()), 'poc_sample_by_ext': by_ext}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=18000)
