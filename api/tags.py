"""Phase 3.5 Tag API

GET  /tags?prefix=&limit=          자동완성
POST /assets/{id}/tags              태그 부착 (멱등)
DELETE /assets/{id}/tags/{tag_id}   태그 제거 + orphan 청소 (user namespace only)
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg
from psycopg.rows import dict_row
import os

router = APIRouter()
DSN = os.environ.get('DAM_DSN', 'postgresql://dam:dam@localhost:15432/dam')


def get_conn():
    return psycopg.connect(DSN, row_factory=dict_row)


class TagRequest(BaseModel):
    name: str
    namespace: str = 'user'


@router.get('/tags')
def list_tags(prefix: str = '', limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, namespace, name FROM tags WHERE name ILIKE %(p)s ORDER BY name LIMIT %(l)s",
            {'p': f'{prefix}%', 'l': limit},
        ).fetchall()
    return {'tags': rows}


@router.post('/assets/{asset_id}/tags', status_code=201)
def add_tag(
    asset_id: int,
    body: TagRequest,
    x_user: Optional[str] = Header(default='anonymous'),
):
    with get_conn() as conn:
        # Upsert tag row
        tag = conn.execute(
            """
            INSERT INTO tags (namespace, name, created_by)
            VALUES (%(ns)s, %(name)s, %(user)s)
            ON CONFLICT (namespace, name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id, namespace, name
            """,
            {'ns': body.namespace, 'name': body.name, 'user': x_user},
        ).fetchone()

        # Upsert asset_tags link
        conn.execute(
            """
            INSERT INTO asset_tags (asset_id, tag_id, added_by)
            VALUES (%(aid)s, %(tid)s, %(user)s)
            ON CONFLICT DO NOTHING
            """,
            {'aid': asset_id, 'tid': tag['id'], 'user': x_user},
        )
        conn.commit()
    return {'tag': tag, 'asset_id': asset_id}


@router.delete('/assets/{asset_id}/tags/{tag_id}', status_code=204)
def remove_tag(
    asset_id: int,
    tag_id: int,
    x_user: Optional[str] = Header(default='anonymous'),
):
    with get_conn() as conn:
        # Check tag namespace before deleting
        tag = conn.execute(
            "SELECT namespace FROM tags WHERE id = %s", (tag_id,)
        ).fetchone()
        if not tag:
            raise HTTPException(404, 'tag not found')

        conn.execute(
            "DELETE FROM asset_tags WHERE asset_id = %s AND tag_id = %s",
            (asset_id, tag_id),
        )

        # Orphan cleanup: only for user namespace
        if tag['namespace'] == 'user':
            remaining = conn.execute(
                "SELECT COUNT(*) AS n FROM asset_tags WHERE tag_id = %s", (tag_id,)
            ).fetchone()['n']
            if remaining == 0:
                conn.execute("DELETE FROM tags WHERE id = %s", (tag_id,))

        conn.commit()
