"""Phase 3.5 Collections API

GET    /collections?owner=          목록 (viewer)
POST   /collections                 생성 (editor)
DELETE /collections/{id}            삭제 (editor)
POST   /collections/{id}/assets     자산 일괄 추가 (editor)
DELETE /collections/{id}/assets/{asset_id}  자산 제거 (editor)
GET    /collections/{id}/assets     자산 목록 (viewer)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg
from psycopg.rows import dict_row
import os

from api.auth import User, require_user

router = APIRouter()
DSN = os.environ.get('DAM_DSN', 'postgresql://dam:dam@localhost:15432/dam')


def get_conn():
    return psycopg.connect(DSN, row_factory=dict_row)


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AssetAdd(BaseModel):
    asset_ids: list[int]


@router.get('/collections')
def list_collections(
    owner: Optional[str] = None,
    user: User = Depends(require_user('viewer')),
):
    with get_conn() as conn:
        if owner:
            rows = conn.execute(
                "SELECT id, name, description, created_by, created_at FROM collections WHERE created_by = %s ORDER BY created_at DESC",
                (owner,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, description, created_by, created_at FROM collections ORDER BY created_at DESC"
            ).fetchall()
    return {'collections': rows}


@router.post('/collections', status_code=201)
def create_collection(
    body: CollectionCreate,
    user: User = Depends(require_user('editor')),
):
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO collections (name, description, created_by)
            VALUES (%(name)s, %(desc)s, %(user)s)
            ON CONFLICT (created_by, name) DO UPDATE SET description = EXCLUDED.description
            RETURNING id, name, description, created_by, created_at
            """,
            {'name': body.name, 'desc': body.description, 'user': user.username},
        ).fetchone()
        conn.commit()
    return row


@router.delete('/collections/{collection_id}', status_code=204)
def delete_collection(
    collection_id: int,
    user: User = Depends(require_user('editor')),
):
    with get_conn() as conn:
        conn.execute("DELETE FROM collections WHERE id = %s", (collection_id,))
        conn.commit()


@router.post('/collections/{collection_id}/assets', status_code=201)
def add_assets(
    collection_id: int,
    body: AssetAdd,
    user: User = Depends(require_user('editor')),
):
    with get_conn() as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM collection_assets WHERE collection_id = %s",
            (collection_id,),
        ).fetchone()['max_order']

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO collection_assets (collection_id, asset_id, sort_order)
                VALUES (%(cid)s, %(aid)s, %(order)s)
                ON CONFLICT DO NOTHING
                """,
                [
                    {'cid': collection_id, 'aid': aid, 'order': max_order + i + 1}
                    for i, aid in enumerate(body.asset_ids)
                ],
            )
        conn.commit()
    return {'collection_id': collection_id, 'added': len(body.asset_ids)}


@router.delete('/collections/{collection_id}/assets/{asset_id}', status_code=204)
def remove_asset(
    collection_id: int,
    asset_id: int,
    user: User = Depends(require_user('editor')),
):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM collection_assets WHERE collection_id = %s AND asset_id = %s",
            (collection_id, asset_id),
        )
        conn.commit()


@router.get('/collections/{collection_id}/assets')
def get_collection_assets(
    collection_id: int,
    user: User = Depends(require_user('viewer')),
):
    with get_conn() as conn:
        assets = conn.execute(
            """
            SELECT ca.asset_id, ca.sort_order, ca.added_at,
                   a.filename, a.primary_ext, a.size_bytes, a.thumbnail_path
            FROM collection_assets ca
            JOIN assets a ON a.id = ca.asset_id
            WHERE ca.collection_id = %s
            ORDER BY ca.sort_order ASC NULLS LAST
            """,
            (collection_id,),
        ).fetchall()
    return {'collection_id': collection_id, 'assets': assets}
