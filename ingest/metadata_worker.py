#!/usr/bin/env python3
"""Phase 3.2 metadata worker — EXIF/tokens/year/role extraction.

실행:
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
    DAM_REALM=poc_sample DAM_BATCH=500 DAM_WORKERS=4 \
    .venv/bin/python ingest/metadata_worker.py > dam_data/poc_metadata.log 2>&1 &
"""

import os, re, sys, json, time, logging, unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit("psycopg 미설치. 실행: pip install 'psycopg[binary]'")

try:
    from PIL import Image, ExifTags, UnidentifiedImageError
except ImportError:
    sys.exit("Pillow 미설치. 실행: pip install Pillow")

from role_keywords import TOKEN_TO_ROLE

DSN      = os.environ.get("DAM_DSN",     "postgresql://dam:dam@localhost:15432/dam")
REALM    = os.environ.get("DAM_REALM",   "poc_sample")
BATCH    = int(os.environ.get("DAM_BATCH",   "500"))
WORKERS  = int(os.environ.get("DAM_WORKERS", "4"))

# Source path remap: for accessing local copies when source is NAS-mounted
_SRC_REMAP_RAW = os.environ.get('SRC_REMAP', '')
_REMAP_OLD, _REMAP_NEW = (_SRC_REMAP_RAW.split('=', 1) if '=' in _SRC_REMAP_RAW else (None, None))

def _remap_src(path: str) -> str:
    if _REMAP_OLD and path.startswith(_REMAP_OLD):
        return _REMAP_NEW + path[len(_REMAP_OLD):]
    return path

YEAR_RE  = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")  # word-bounded 4-digit year
# Split on path separators, underscores, hyphens, spaces, dots
TOKEN_SEP = re.compile(r"[/\\_.+\-\s]+")
# Detect CJK/Latin/digit boundary for splitting mixed tokens
BOUNDARY  = re.compile(
    r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])"
    r"|(?<=\w)(?=[가-힣一-鿿])"
    r"|(?<=[가-힣一-鿿])(?=\w)"
)

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp",
    ".bmp", ".gif", ".heic", ".heif", ".psd",
}


def _extract_exif(path: str) -> dict | None:
    ext = Path(path).suffix.lower()
    if ext not in IMAGE_EXTS:
        return None
    try:
        with Image.open(path) as img:
            raw = img.getexif()
            if not raw:
                return {}
            data = {}
            for tag_id, value in raw.items():
                tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                # Skip large binary blobs (preview images etc.)
                if isinstance(value, bytes) and len(value) > 512:
                    continue
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="replace")
                    except Exception:
                        continue
                v = str(value) if not isinstance(value, (int, float, str)) else value
                # Strip null bytes — PostgreSQL rejects  in JSONB
                if isinstance(v, str):
                    v = v.replace("\x00", "")
                data[tag] = v
            return data
    except (UnidentifiedImageError, Exception):
        return None


def _folder_tokens(physical_path: str) -> list[str]:
    parts = re.split(r"[/\\]", physical_path)
    # Drop the filename (last part) and empty strings
    tokens = [p for p in parts[:-1] if p and len(p) > 1 and p not in (".", "..")]
    return tokens


def _filename_tokens(filename: str) -> list[str]:
    base = Path(filename).stem.lower()
    # First split on separators
    raw = TOKEN_SEP.split(base)
    # Then split on char-class boundaries
    parts: list[str] = []
    for chunk in raw:
        parts.extend(BOUNDARY.split(chunk))
    return [t for t in parts if len(t) >= 2]


def _year_hint(physical_path: str, filename: str) -> int | None:
    combined = physical_path + "/" + filename
    years = [int(m) for m in YEAR_RE.findall(combined)]
    return max(years) if years else None


def _role_hint(folder_tokens: list[str], filename_tokens: list[str]) -> list[str]:
    # Use substring matching: Korean folder names are compound words (e.g. "가로포스터")
    combined = " ".join(t.lower() for t in folder_tokens + filename_tokens)
    roles: set[str] = set()
    for keyword, role in TOKEN_TO_ROLE.items():
        if keyword in combined:
            roles.add(role)
    return sorted(roles)


def process(asset_id: int, physical_path: str) -> dict:
    filename = Path(physical_path).name
    exif = _extract_exif(_remap_src(physical_path))  # None = skip (non-image or error)
    ftoks = _folder_tokens(physical_path)
    ntoks = _filename_tokens(filename)
    year = _year_hint(physical_path, filename)
    roles = _role_hint(ftoks, ntoks)
    return {
        "asset_id":       asset_id,
        "metadata_json":  json.dumps(exif) if exif is not None else None,
        "folder_tokens":  ftoks,
        "filename_tokens": ntoks,
        "year_hint":      year,
        "role_hint":      roles if roles else None,
    }


def run():
    t0 = time.time()
    with psycopg.connect(DSN) as conn:
        # Count total
        total = conn.execute(
            "SELECT COUNT(*) FROM asset_storage WHERE realm = %s", (REALM,)
        ).fetchone()[0]
        log.info(f"총 {total:,}건 처리 시작 (realm={REALM}, workers={WORKERS}, batch={BATCH})")

        processed = 0
        errors = 0

        while True:
            # Always query without OFFSET: as rows are updated (folder_tokens no longer NULL),
            # the next fetch naturally picks up remaining unprocessed rows.
            rows = conn.execute(
                """
                SELECT s.asset_id, s.physical_path
                FROM asset_storage s
                WHERE s.realm = %s
                  AND EXISTS (
                      SELECT 1 FROM assets a
                      WHERE a.id = s.asset_id AND a.folder_tokens IS NULL
                  )
                ORDER BY s.asset_id
                LIMIT %s
                """,
                (REALM, BATCH),
            ).fetchall()

            if not rows:
                break

            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                futures = {
                    pool.submit(process, row[0], row[1]): row[0]
                    for row in rows
                }
                results = []
                for fut in as_completed(futures):
                    try:
                        results.append(fut.result())
                    except Exception as e:
                        errors += 1
                        log.warning(f"asset {futures[fut]} error: {e}")

            if results:
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        UPDATE assets SET
                          metadata_json   = %(metadata_json)s,
                          folder_tokens   = %(folder_tokens)s,
                          filename_tokens = %(filename_tokens)s,
                          year_hint       = %(year_hint)s,
                          role_hint       = %(role_hint)s
                        WHERE id = %(asset_id)s
                        """,
                        results,
                    )
                conn.commit()

            processed += len(rows)
            elapsed = time.time() - t0
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else 0
            log.info(
                f"[{processed:,}/{total:,}] errors={errors} "
                f"rate={rate:.0f}/s eta={eta/60:.1f}min"
            )

        elapsed = time.time() - t0
        log.info(f"완료: {processed:,}건, errors={errors}, elapsed={elapsed:.0f}s")


if __name__ == "__main__":
    run()
