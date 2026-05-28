"""Phase 3.5 Tag API

GET  /tags?prefix=&limit=          자동완성 (viewer)
POST /assets/{id}/tags              태그 부착 멱등 (editor)
DELETE /assets/{id}/tags/{tag_id}   태그 제거 + orphan 청소 (editor)
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


class TagRequest(BaseModel):
    name: str
    namespace: str = 'user'


@router.get('/tags')
def list_tags(
    prefix: str = '',
    limit: int = 20,
    user: User = Depends(require_user('viewer')),
):
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
    user: User = Depends(require_user('editor')),
):
    with get_conn() as conn:
        tag = conn.execute(
            """
            INSERT INTO tags (namespace, name, created_by)
            VALUES (%(ns)s, %(name)s, %(user)s)
            ON CONFLICT (namespace, name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id, namespace, name
            """,
            {'ns': body.namespace, 'name': body.name, 'user': user.username},
        ).fetchone()

        conn.execute(
            """
            INSERT INTO asset_tags (asset_id, tag_id, added_by)
            VALUES (%(aid)s, %(tid)s, %(user)s)
            ON CONFLICT DO NOTHING
            """,
            {'aid': asset_id, 'tid': tag['id'], 'user': user.username},
        )
        conn.commit()
    return {'tag': tag, 'asset_id': asset_id}


@router.delete('/assets/{asset_id}/tags/{tag_id}', status_code=204)
def remove_tag(
    asset_id: int,
    tag_id: int,
    user: User = Depends(require_user('editor')),
):
    with get_conn() as conn:
        tag = conn.execute(
            "SELECT namespace FROM tags WHERE id = %s", (tag_id,)
        ).fetchone()
        if not tag:
            raise HTTPException(404, 'tag not found')

        conn.execute(
            "DELETE FROM asset_tags WHERE asset_id = %s AND tag_id = %s",
            (asset_id, tag_id),
        )

        if tag['namespace'] == 'user':
            remaining = conn.execute(
                "SELECT COUNT(*) AS n FROM asset_tags WHERE tag_id = %s", (tag_id,)
            ).fetchone()['n']
            if remaining == 0:
                conn.execute("DELETE FROM tags WHERE id = %s", (tag_id,))

        conn.commit()
