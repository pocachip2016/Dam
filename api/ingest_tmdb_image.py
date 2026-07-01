"""
tmdb-image ingest API — TMDB 이미지 → Dam tmdb_cas 독립 캐시 등록

엔드포인트:
  POST /api/ingest/tmdb-image   TMDB 이미지 다운로드 → tmdb_cas CAS 등록
  GET  /api/ingest/tmdb-image/status   자연키 기준 상태 조회

mediaX content_id에 미종속 — entity_type+tmdb_id+image_kind+file_path 자연키로
멱등 처리한다. 향후 서비스 콘텐츠로 채택될 경우 asset_content_link(asset_id,
content_id) INSERT만으로 연결 가능(이 모듈은 변경 불필요).
"""
import os
import sys
from pathlib import Path
from typing import Optional

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit("psycopg 미설치")

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import User, require_user
from api.ingest_poster import _download, _sha256_of_bytes

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

_admin = Depends(require_user("admin"))

DB_DSN = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")
DAM_TMDB_CAS_ROOT = Path(
    os.environ.get("DAM_TMDB_CAS_ROOT", str(Path.home() / "Work/Dam/dam_data/tmdb_cas"))
)
_VALID_ENTITY_TYPES = {"movie", "tv", "person"}
_VALID_IMAGE_KINDS = {"poster", "backdrop", "logo", "still", "profile"}


def _conn():
    return psycopg.connect(DB_DSN, row_factory=dict_row)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class TmdbImageIngestRequest(BaseModel):
    entity_type: str
    tmdb_id: int
    image_kind: str
    file_path: str      # TMDB 상대 경로 (자연키 일부)
    image_url: str       # 다운로드용 완전 CDN URL


class TmdbImageIngestResponse(BaseModel):
    status: str          # "ok" | "skipped" | "failed"
    asset_id: Optional[int] = None
    message: str = ""


# ── Helper ────────────────────────────────────────────────────────────────────

def _save_file(sha256: str, data: bytes) -> Path:
    dest_dir = DAM_TMDB_CAS_ROOT / sha256[:2]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha256}.jpg"
    if not dest.exists():
        dest.write_bytes(data)
    return dest


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/tmdb-image", response_model=TmdbImageIngestResponse)
def ingest_tmdb_image(req: TmdbImageIngestRequest, user: User = _admin):
    """
    TMDB 이미지를 (entity_type, tmdb_id, image_kind, file_path) 자연키 기준
    idempotent하게 다운로드해 tmdb_cas에 저장한다. mediaX content_id 불필요.
    """
    if req.entity_type not in _VALID_ENTITY_TYPES:
        raise HTTPException(400, f"entity_type must be one of {_VALID_ENTITY_TYPES}")
    if req.image_kind not in _VALID_IMAGE_KINDS:
        raise HTTPException(400, f"image_kind must be one of {_VALID_IMAGE_KINDS}")

    with _conn() as conn:
        with conn.cursor() as cur:
            # 1. 자연키 기준 중복 확인 (idempotency)
            cur.execute(
                """
                SELECT id, status, asset_id FROM tmdb_image_ingest_log
                WHERE entity_type = %s AND tmdb_id = %s
                  AND image_kind = %s AND file_path = %s
                """,
                (req.entity_type, req.tmdb_id, req.image_kind, req.file_path),
            )
            existing = cur.fetchone()
            if existing and existing["status"] == "downloaded":
                return TmdbImageIngestResponse(
                    status="skipped",
                    asset_id=existing["asset_id"],
                    message="already ingested",
                )

            # 2. pending 행 INSERT (없을 경우에만)
            if existing is None:
                cur.execute(
                    """
                    INSERT INTO tmdb_image_ingest_log
                        (entity_type, tmdb_id, image_kind, file_path, source_url, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    RETURNING id
                    """,
                    (req.entity_type, req.tmdb_id, req.image_kind, req.file_path, req.image_url),
                )
                log_id = cur.fetchone()["id"]
            else:
                log_id = existing["id"]
                cur.execute(
                    "UPDATE tmdb_image_ingest_log SET status='pending', error_msg=NULL WHERE id=%s",
                    (log_id,),
                )
        conn.commit()

        # 3. 파일 다운로드
        try:
            data = _download(req.image_url)
        except Exception as exc:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tmdb_image_ingest_log SET status='failed', error_msg=%s WHERE id=%s",
                    (str(exc)[:500], log_id),
                )
            conn.commit()
            raise HTTPException(502, f"download failed: {exc}")

        sha256 = _sha256_of_bytes(data)

        # 4. 파일 저장 (sha256 샤딩 — content_id 없으므로)
        try:
            dest = _save_file(sha256, data)
        except Exception as exc:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tmdb_image_ingest_log SET status='failed', error_msg=%s WHERE id=%s",
                    (f"save error: {exc}"[:500], log_id),
                )
            conn.commit()
            raise HTTPException(500, f"file save failed: {exc}")

        physical_path = str(dest)

        with conn.cursor() as cur:
            # 5. sha256 중복 asset 체크
            cur.execute("SELECT id FROM assets WHERE sha256 = %s", (sha256,))
            asset_row = cur.fetchone()

            if asset_row:
                asset_id = asset_row["id"]
            else:
                # 6. assets INSERT
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

                # 7. asset_storage INSERT (realm='tmdb_cas')
                cur.execute(
                    """
                    INSERT INTO asset_storage (asset_id, realm, physical_path, is_authoritative)
                    VALUES (%s, 'tmdb_cas', %s, true)
                    ON CONFLICT (realm, physical_path) DO NOTHING
                    """,
                    (asset_id, physical_path),
                )

            # 8. tmdb_image_ingest_log 완료 처리
            cur.execute(
                """
                UPDATE tmdb_image_ingest_log
                SET status='downloaded', sha256=%s, asset_id=%s, processed_at=now()
                WHERE id=%s
                """,
                (sha256, asset_id, log_id),
            )

        conn.commit()

    return TmdbImageIngestResponse(
        status="ok",
        asset_id=asset_id,
        message=f"saved to {physical_path}",
    )


@router.get("/tmdb-image/status", response_model=TmdbImageIngestResponse)
def tmdb_image_status(
    entity_type: str, tmdb_id: int, image_kind: str, file_path: str, user: User = _admin
):
    """자연키로 ingest 상태 조회."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, asset_id, error_msg FROM tmdb_image_ingest_log
                WHERE entity_type=%s AND tmdb_id=%s AND image_kind=%s AND file_path=%s
                """,
                (entity_type, tmdb_id, image_kind, file_path),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "no ingest log for given natural key")
    return TmdbImageIngestResponse(
        status=row["status"],
        asset_id=row["asset_id"],
        message=row["error_msg"] or "",
    )
