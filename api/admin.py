"""
Admin API — 분류·매핑 human review + worker 모니터링.

엔드포인트:
  POST /api/admin/classification/{asset_id}/{class}/confirm
  POST /api/admin/classification/{asset_id}/{class}/reject
  POST /api/admin/classification/reclass   body: {asset_id, old_class, new_class}
  POST /api/admin/mapping/{asset_id}/{content_id}/confirm
  POST /api/admin/mapping/{asset_id}/{content_id}/reject
  POST /api/admin/mapping/add              body: {asset_id, content_id, note?}
  POST /api/admin/unclassified/bulk-classify  body: {asset_ids, class, sub_class?}
  GET  /api/admin/workers?limit=20         → 최근 run 목록 + 진행률 + ETA
  GET  /api/admin/workers/{id}             → 단일 run 상세
"""
import os
import sys
from typing import Optional

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit("psycopg 미설치")

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import User, require_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

_admin = Depends(require_user("admin"))

DB_DSN = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")

_VALID_CLASSES = {
    "content", "promotion", "seasonal", "pricing", "branding",
    "ui_service", "composition", "draft", "unclassified",
}


def _conn():
    return psycopg.connect(DB_DSN, row_factory=dict_row)


# ── Classification ────────────────────────────────────────────────────────────

@router.post("/classification/{asset_id}/{cls}/confirm")
def confirm_classification(asset_id: int, cls: str, user: User = _admin):
    if cls not in _VALID_CLASSES:
        raise HTTPException(400, f"invalid class: {cls}")
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE asset_classifications SET status='confirmed', updated_at=now()"
                " WHERE asset_id=%s AND class=%s",
                (asset_id, cls),
            )
            if cur.rowcount == 0:
                raise HTTPException(404, "classification not found")
        conn.commit()
    return {"asset_id": asset_id, "class": cls, "status": "confirmed"}


@router.post("/classification/{asset_id}/{cls}/reject")
def reject_classification(asset_id: int, cls: str, user: User = _admin):
    if cls not in _VALID_CLASSES:
        raise HTTPException(400, f"invalid class: {cls}")
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE asset_classifications SET status='rejected', updated_at=now()"
                " WHERE asset_id=%s AND class=%s",
                (asset_id, cls),
            )
            if cur.rowcount == 0:
                raise HTTPException(404, "classification not found")
        conn.commit()
    return {"asset_id": asset_id, "class": cls, "status": "rejected"}


class ReclassBody(BaseModel):
    asset_id:  int
    old_class: str
    new_class: str
    sub_class: Optional[str] = None


@router.post("/classification/reclass")
def reclass(body: ReclassBody, user: User = _admin):
    if body.new_class not in _VALID_CLASSES:
        raise HTTPException(400, f"invalid new_class: {body.new_class}")
    with _conn() as conn:
        with conn.cursor() as cur:
            # 기존 클래스 rejected, 신규 클래스 upsert (candidate)
            cur.execute(
                "UPDATE asset_classifications SET status='rejected', updated_at=now()"
                " WHERE asset_id=%s AND class=%s",
                (body.asset_id, body.old_class),
            )
            cur.execute(
                """
                INSERT INTO asset_classifications
                  (asset_id, class, sub_class, confidence, method, matched_signal, status)
                VALUES (%s, %s, %s, 1.0, 'manual', 'reclass', 'confirmed')
                ON CONFLICT (asset_id, class) DO UPDATE SET
                  sub_class  = EXCLUDED.sub_class,
                  status     = 'confirmed',
                  method     = 'manual',
                  updated_at = now()
                """,
                (body.asset_id, body.new_class, body.sub_class),
            )
        conn.commit()
    return {"asset_id": body.asset_id, "old_class": body.old_class,
            "new_class": body.new_class, "status": "confirmed"}


# ── Content Mapping ───────────────────────────────────────────────────────────

@router.post("/mapping/{asset_id}/{content_id}/confirm")
def confirm_mapping(asset_id: int, content_id: int, user: User = _admin):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE asset_content_link SET status='confirmed', updated_at=now()"
                " WHERE asset_id=%s AND content_id=%s",
                (asset_id, content_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(404, "mapping not found")
        conn.commit()
    return {"asset_id": asset_id, "content_id": content_id, "status": "confirmed"}


@router.post("/mapping/{asset_id}/{content_id}/reject")
def reject_mapping(asset_id: int, content_id: int, user: User = _admin):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE asset_content_link SET status='rejected', updated_at=now()"
                " WHERE asset_id=%s AND content_id=%s",
                (asset_id, content_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(404, "mapping not found")
        conn.commit()
    return {"asset_id": asset_id, "content_id": content_id, "status": "rejected"}


class AddMappingBody(BaseModel):
    asset_id:   int
    content_id: int
    note:       Optional[str] = None


@router.post("/mapping/add")
def add_mapping(body: AddMappingBody, user: User = _admin):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO asset_content_link
                  (asset_id, content_id, confidence, method, status)
                VALUES (%s, %s, 1.0, 'manual', 'confirmed')
                ON CONFLICT (asset_id, content_id) DO UPDATE SET
                  method     = 'manual',
                  confidence = 1.0,
                  status     = 'confirmed',
                  updated_at = now()
                """,
                (body.asset_id, body.content_id),
            )
        conn.commit()
    return {"asset_id": body.asset_id, "content_id": body.content_id, "status": "confirmed"}


# ── Unclassified bulk ─────────────────────────────────────────────────────────

class BulkClassifyBody(BaseModel):
    asset_ids: list[int]
    cls:       str
    sub_class: Optional[str] = None


@router.post("/unclassified/bulk-classify")
def bulk_classify(body: BulkClassifyBody, user: User = _admin):
    if body.cls not in _VALID_CLASSES:
        raise HTTPException(400, f"invalid class: {body.cls}")
    if not body.asset_ids:
        raise HTTPException(400, "asset_ids 비어있음")
    if len(body.asset_ids) > 500:
        raise HTTPException(400, "최대 500건씩 처리")

    with _conn() as conn:
        with conn.cursor() as cur:
            rows = [
                (aid, body.cls, body.sub_class, 1.0, "manual", "bulk_classify", "confirmed")
                for aid in body.asset_ids
            ]
            cur.executemany(
                """
                INSERT INTO asset_classifications
                  (asset_id, class, sub_class, confidence, method, matched_signal, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset_id, class) DO UPDATE SET
                  sub_class      = EXCLUDED.sub_class,
                  method         = 'manual',
                  status         = 'confirmed',
                  updated_at     = now()
                """,
                rows,
            )
        conn.commit()
    return {"classified": len(body.asset_ids), "class": body.cls, "status": "confirmed"}


# ── Worker Monitoring ─────────────────────────────────────────────────────────

def _eta_seconds(row: dict) -> float | None:
    """선형 보간 ETA (초). 계산 불가 시 None."""
    if not row.get("total_planned") or not row.get("processed"):
        return None
    elapsed = (row["last_heartbeat"] - row["started_at"]).total_seconds()
    if elapsed <= 0:
        return None
    rate = row["processed"] / elapsed
    remaining = row["total_planned"] - row["processed"]
    return remaining / rate if rate > 0 else None


@router.get("/workers")
def list_worker_runs(limit: int = Query(20, ge=1, le=200), user: User = _admin):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, worker_name, started_at, finished_at,
                       total_planned, processed, errors, last_heartbeat, notes
                FROM worker_runs
                ORDER BY started_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    result = []
    for r in rows:
        pct = round(r["processed"] / r["total_planned"] * 100, 1) if r["total_planned"] else None
        eta = _eta_seconds(r) if not r["finished_at"] else None
        result.append({
            **r,
            "progress_pct": pct,
            "eta_seconds": round(eta) if eta is not None else None,
        })
    return result


@router.get("/workers/{run_id}")
def get_worker_run(run_id: int, user: User = _admin):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, worker_name, started_at, finished_at,
                       total_planned, processed, errors, last_heartbeat, notes
                FROM worker_runs WHERE id = %s
                """,
                (run_id,),
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, "run not found")
    pct = round(row["processed"] / row["total_planned"] * 100, 1) if row["total_planned"] else None
    eta = _eta_seconds(row) if not row["finished_at"] else None
    return {**row, "progress_pct": pct, "eta_seconds": round(eta) if eta is not None else None}
