"""
M.2 read-only mapping stats/query API.

엔드포인트:
  GET /api/mapping/stats
  GET /api/mapping/by-content/{content_id}
  GET /api/mapping/by-class/{class}?status=&page=&size=
  GET /api/mapping/asset/{asset_id}
"""
import os
import sys

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit("psycopg 미설치")

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import User, require_user

router = APIRouter(prefix="/api/mapping", tags=["mapping"])

_admin = Depends(require_user("admin"))

DB_DSN = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")


def _conn():
    return psycopg.connect(DB_DSN, row_factory=dict_row)


@router.get("/stats")
def mapping_stats(user: User = _admin):
    with _conn() as conn:
        with conn.cursor() as cur:
            # class 분포
            cur.execute(
                "SELECT class, status, COUNT(*) AS cnt FROM asset_classifications GROUP BY class, status ORDER BY class, status"
            )
            class_dist = cur.fetchall()

            # confidence 히스토그램 (content 클래스 기준)
            cur.execute("""
                SELECT
                  SUM(CASE WHEN confidence < 0.90 THEN 1 ELSE 0 END)  AS "0.85-0.90",
                  SUM(CASE WHEN confidence >= 0.90 AND confidence < 0.95 THEN 1 ELSE 0 END) AS "0.90-0.95",
                  SUM(CASE WHEN confidence >= 0.95 THEN 1 ELSE 0 END) AS "0.95-1.00"
                FROM asset_classifications WHERE class='content'
            """)
            conf_hist = cur.fetchone()

            # method 비중
            cur.execute(
                "SELECT method, COUNT(*) AS cnt FROM asset_classifications GROUP BY method ORDER BY cnt DESC"
            )
            method_dist = cur.fetchall()

            # 매핑 적중률
            cur.execute("""
                SELECT
                  COUNT(DISTINCT ac.asset_id) FILTER (WHERE ac.class='content') AS content_total,
                  COUNT(DISTINCT acl.asset_id) AS mapped_total
                FROM asset_classifications ac
                LEFT JOIN asset_content_link acl ON acl.asset_id=ac.asset_id
                WHERE ac.class='content'
            """)
            hit = cur.fetchone()

    content_total = hit["content_total"] or 0
    mapped_total  = hit["mapped_total"] or 0
    hit_rate = round(mapped_total / content_total, 4) if content_total else 0.0

    return {
        "class_distribution": [dict(r) for r in class_dist],
        "confidence_histogram": dict(conf_hist) if conf_hist else {},
        "method_distribution": [dict(r) for r in method_dist],
        "mapping_hit_rate": hit_rate,
        "content_total": content_total,
        "mapped_total": mapped_total,
    }


@router.get("/by-content/{content_id}")
def by_content(content_id: int, user: User = _admin):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                  a.id AS asset_id, a.filename, s.physical_path AS folder_path,
                  acl.confidence, acl.method, acl.status
                FROM asset_content_link acl
                JOIN assets a ON a.id = acl.asset_id
                JOIN asset_storage s ON s.asset_id = a.id
                WHERE acl.content_id = %s
                ORDER BY acl.confidence DESC
            """, (content_id,))
            rows = cur.fetchall()
    if not rows:
        raise HTTPException(404, f"content_id {content_id} 매핑 없음")
    return {"content_id": content_id, "assets": [dict(r) for r in rows]}


_VALID_CLASSES = {
    "content", "promotion", "seasonal", "pricing", "branding",
    "ui_service", "composition", "draft", "unclassified",
}


@router.get("/by-class/{cls}")
def by_class(
    cls: str,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    user: User = _admin,
):
    if cls not in _VALID_CLASSES:
        raise HTTPException(400, f"invalid class: {cls}")
    offset = (page - 1) * size

    with _conn() as conn:
        with conn.cursor() as cur:
            base = (
                "FROM asset_classifications ac "
                "JOIN assets a ON a.id=ac.asset_id "
                "JOIN asset_storage s ON s.asset_id=a.id "
                "WHERE ac.class=%s"
            )
            params: list = [cls]
            if status:
                base += " AND ac.status=%s"
                params.append(status)

            cur.execute(f"SELECT COUNT(*) AS cnt {base}", params)
            total = cur.fetchone()["cnt"]

            cur.execute(
                f"""SELECT a.id AS asset_id, a.filename, s.physical_path AS folder_path,
                           ac.sub_class, ac.confidence, ac.method, ac.status
                    {base} ORDER BY ac.confidence DESC LIMIT %s OFFSET %s""",
                params + [size, offset],
            )
            rows = cur.fetchall()

    return {"class": cls, "total": total, "page": page, "size": size, "assets": [dict(r) for r in rows]}


@router.get("/contents")
def search_contents(
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    user: User = _admin,
):
    with _conn() as conn:
        with conn.cursor() as cur:
            if q:
                cur.execute(
                    """SELECT content_id, title, original_title, content_type, production_year
                       FROM content_catalog_mirror
                       WHERE title ILIKE %s OR original_title ILIKE %s
                       ORDER BY title
                       LIMIT %s""",
                    (f"%{q}%", f"%{q}%", limit),
                )
            else:
                cur.execute(
                    """SELECT content_id, title, original_title, content_type, production_year
                       FROM content_catalog_mirror
                       ORDER BY title
                       LIMIT %s""",
                    (limit,),
                )
            rows = cur.fetchall()
    return {"q": q, "limit": limit, "results": [dict(r) for r in rows]}


@router.get("/asset/{asset_id}")
def asset_detail(asset_id: int, user: User = _admin):
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT class, sub_class, confidence, method, matched_signal, status FROM asset_classifications WHERE asset_id=%s",
                (asset_id,),
            )
            classes = cur.fetchall()
            if not classes:
                raise HTTPException(404, f"asset {asset_id} 분류 없음")

            cur.execute("""
                SELECT acl.content_id, ccm.title, acl.confidence, acl.method, acl.status
                FROM asset_content_link acl
                JOIN content_catalog_mirror ccm ON ccm.content_id=acl.content_id
                WHERE acl.asset_id=%s ORDER BY acl.confidence DESC
            """, (asset_id,))
            links = cur.fetchall()

    return {
        "asset_id": asset_id,
        "classifications": [dict(r) for r in classes],
        "content_links": [dict(r) for r in links],
    }
