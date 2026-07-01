"""
poster ingest API — mediaX primary 포스터 → Dam 자동 등록

엔드포인트:
  POST /api/ingest/poster   mediaX webhook 수신 → URL 다운로드 → assets 등록
  GET  /api/ingest/poster/status/{image_id}   등록 상태 조회
"""
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import httpx
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit("httpx 또는 psycopg 미설치")

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from api.auth import User, require_user

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

_admin = Depends(require_user("admin"))

DB_DSN = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")
DAM_POSTER_ROOT = Path(
    os.environ.get("DAM_POSTER_ROOT", str(Path.home() / "Work/Dam/dam_data/posters"))
)
_VALID_SOURCES = {"tmdb", "cp_upload", "ai_generated", "web_crawl"}


def _conn():
    return psycopg.connect(DB_DSN, row_factory=dict_row)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class PosterIngestRequest(BaseModel):
    content_id: int
    image_id: int
    poster_url: str
    poster_source: str = "tmdb"
    title: Optional[str] = None


class PosterIngestResponse(BaseModel):
    status: str          # "ok" | "skipped"
    image_id: int
    asset_id: Optional[int] = None
    message: str = ""


# ── Helper ────────────────────────────────────────────────────────────────────

def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(url: str, timeout: float = 30.0) -> bytes:
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        resp = client.get(url)
    resp.raise_for_status()
    return resp.content


def _save_file(content_id: int, sha256: str, data: bytes) -> Path:
    dest_dir = DAM_POSTER_ROOT / str(content_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha256}.jpg"
    if not dest.exists():
        dest.write_bytes(data)
    return dest


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/poster", response_model=PosterIngestResponse)
def ingest_poster(req: PosterIngestRequest, user: User = _admin):
    """
    mediaX에서 primary 포스터 지정 시 호출.
    image_id 기준 idempotent — 이미 처리된 image_id면 asset_id와 함께 즉시 반환.
    """
    if req.poster_source not in _VALID_SOURCES:
        raise HTTPException(400, f"poster_source must be one of {_VALID_SOURCES}")

    with _conn() as conn:
        with conn.cursor() as cur:
            # 1. content_catalog_mirror 존재 확인
            cur.execute(
                "SELECT content_id FROM content_catalog_mirror WHERE content_id = %s",
                (req.content_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(
                    404,
                    f"content_id {req.content_id} not in content_catalog_mirror — "
                    "mediaX mirror may not have synced yet",
                )

            # 2. image_id 중복 확인 (idempotency)
            cur.execute(
                "SELECT id, status, asset_id FROM poster_ingest_log WHERE image_id = %s",
                (req.image_id,),
            )
            existing = cur.fetchone()
            if existing and existing["status"] == "downloaded":
                return PosterIngestResponse(
                    status="skipped",
                    image_id=req.image_id,
                    asset_id=existing["asset_id"],
                    message="already ingested",
                )

            # 3. pending 행 INSERT (없을 경우에만)
            if existing is None:
                cur.execute(
                    """
                    INSERT INTO poster_ingest_log
                        (content_id, image_id, poster_source, source_url, status)
                    VALUES (%s, %s, %s, %s, 'pending')
                    RETURNING id
                    """,
                    (req.content_id, req.image_id, req.poster_source, req.poster_url),
                )
                log_id = cur.fetchone()["id"]
            else:
                log_id = existing["id"]
                cur.execute(
                    "UPDATE poster_ingest_log SET status='pending', error_msg=NULL WHERE id=%s",
                    (log_id,),
                )
        conn.commit()

        # 4. 파일 다운로드
        try:
            data = _download(req.poster_url)
        except Exception as exc:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE poster_ingest_log SET status='failed', error_msg=%s WHERE id=%s",
                    (str(exc)[:500], log_id),
                )
            conn.commit()
            raise HTTPException(502, f"download failed: {exc}")

        sha256 = _sha256_of_bytes(data)

        # 5. 파일 저장
        try:
            dest = _save_file(req.content_id, sha256, data)
        except Exception as exc:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE poster_ingest_log SET status='failed', error_msg=%s WHERE id=%s",
                    (f"save error: {exc}"[:500], log_id),
                )
            conn.commit()
            raise HTTPException(500, f"file save failed: {exc}")

        physical_path = str(dest)

        with conn.cursor() as cur:
            # 6. sha256 중복 asset 체크
            cur.execute("SELECT id FROM assets WHERE sha256 = %s", (sha256,))
            asset_row = cur.fetchone()

            if asset_row:
                asset_id = asset_row["id"]
            else:
                # 7. assets INSERT
                filename = dest.name
                cur.execute(
                    """
                    INSERT INTO assets (filename, sha256, size_bytes, asset_type)
                    VALUES (%s, %s, %s, 'source')
                    RETURNING id
                    """,
                    (filename, sha256, len(data)),
                )
                asset_id = cur.fetchone()["id"]

                # 8. asset_storage INSERT (realm='dam_cas')
                cur.execute(
                    """
                    INSERT INTO asset_storage (asset_id, realm, physical_path, is_authoritative)
                    VALUES (%s, 'dam_cas', %s, true)
                    ON CONFLICT (realm, physical_path) DO NOTHING
                    """,
                    (asset_id, physical_path),
                )

            # 9. asset_content_link UPSERT
            cur.execute(
                """
                INSERT INTO asset_content_link
                    (asset_id, content_id, method, confidence, status, updated_at)
                VALUES (%s, %s, 'mediax_webhook', 1.0, 'confirmed', now())
                ON CONFLICT (asset_id, content_id)
                DO UPDATE SET
                    method = EXCLUDED.method,
                    confidence = EXCLUDED.confidence,
                    status = EXCLUDED.status,
                    updated_at = now()
                """,
                (asset_id, req.content_id),
            )

            # 10. poster_ingest_log 완료 처리
            cur.execute(
                """
                UPDATE poster_ingest_log
                SET status='downloaded', sha256=%s, asset_id=%s, processed_at=now()
                WHERE id=%s
                """,
                (sha256, asset_id, log_id),
            )

        conn.commit()

    return PosterIngestResponse(
        status="ok",
        image_id=req.image_id,
        asset_id=asset_id,
        message=f"saved to {physical_path}",
    )


@router.get("/poster/status/{image_id}", response_model=PosterIngestResponse)
def poster_status(image_id: int, user: User = _admin):
    """image_id로 포스터 등록 상태 조회."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, asset_id, error_msg FROM poster_ingest_log WHERE image_id=%s",
                (image_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(404, f"image_id {image_id} not found")
    return PosterIngestResponse(
        status=row["status"],
        image_id=image_id,
        asset_id=row["asset_id"],
        message=row["error_msg"] or "",
    )
