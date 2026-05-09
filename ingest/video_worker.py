"""
M.4 video asset worker (oneshot, mock).

Dam 내 영상 파일(mp4/mov/etc.)은 VOD 원본이 아닌 디자인 산출물
(모션 배너, 영상형 UI 자산).
→ 기존 폴더패턴 분류 로직 재활용 + duration_ms best-effort 추출.

환경변수:
  DAM_DSN   (필수)
  DAM_REALM (기본: poc_sample)

실행:
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam .venv/bin/python -m ingest.video_worker
"""
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit("psycopg 미설치")

try:
    from mutagen.mp4 import MP4
    from mutagen import MutagenError
    _HAS_MUTAGEN = True
except ImportError:
    _HAS_MUTAGEN = False

from ._classification_rules import FOLDER_PATTERNS
from ._korean_norm import extract_korean

DSN   = os.environ.get("DAM_DSN",   "postgresql://dam:dam@localhost:15432/dam")
REALM = os.environ.get("DAM_REALM", "poc_sample")

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m2ts", ".ts", ".mts", ".webm"}

_UPSERT_CLASS = """
INSERT INTO asset_classifications
  (asset_id, class, sub_class, confidence, method, matched_signal, status)
VALUES (%s, %s, %s, %s, %s, %s, 'candidate')
ON CONFLICT (asset_id, class) DO UPDATE SET
  sub_class      = EXCLUDED.sub_class,
  confidence     = GREATEST(asset_classifications.confidence, EXCLUDED.confidence),
  method         = EXCLUDED.method,
  matched_signal = EXCLUDED.matched_signal,
  updated_at     = now();
"""


def _get_duration_ms(physical_path: str) -> int | None:
    if not _HAS_MUTAGEN:
        return None
    try:
        audio = MP4(physical_path)
        return int(audio.info.duration * 1000)
    except Exception:
        return None


def _classify_video(folder_path: str, filename: str) -> tuple[str, str | None, float, str]:
    """폴더패턴으로 class 결정. 기본값: composition."""
    for pattern, cls, sub_cls, conf in FOLDER_PATTERNS:
        if pattern.search(folder_path):
            return cls, sub_cls, conf, "folder_pattern"
    return "composition", "video", 0.80, "rule"


def main() -> None:
    log.info("video_worker start — realm=%s mutagen=%s", REALM, _HAS_MUTAGEN)

    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT a.id, a.filename, a.primary_ext, a.duration_ms,
                       COALESCE(s.top_folder || '/' || s.sub_folder, '') AS folder_path,
                       s.physical_path
                FROM assets a
                LEFT JOIN asset_storage s ON s.asset_id=a.id AND s.is_authoritative=true
                WHERE a.primary_ext = ANY(%s)
                  AND s.realm = %s
                ORDER BY a.id
                """,
                (list(VIDEO_EXTS), REALM),
            )
            rows = cur.fetchall()

        log.info("video assets: %d", len(rows))

        class_rows: list[tuple] = []
        duration_updates: list[tuple] = []

        for row in rows:
            aid          = row["id"]
            folder_path  = row["folder_path"] or ""
            filename     = row["filename"] or ""
            physical_path = row["physical_path"] or ""

            cls, sub_cls, conf, method = _classify_video(folder_path, filename)
            class_rows.append((aid, cls, sub_cls, conf, method, folder_path[:200]))

            # duration_ms best-effort (파일 접근 가능할 때만)
            if row["duration_ms"] is None and physical_path:
                duration_ms = _get_duration_ms(physical_path)
                if duration_ms is not None:
                    duration_updates.append((duration_ms, aid))

        with conn.cursor() as cur:
            if class_rows:
                cur.executemany(_UPSERT_CLASS, class_rows)
            if duration_updates:
                cur.executemany(
                    "UPDATE assets SET duration_ms=%s WHERE id=%s",
                    duration_updates,
                )
        conn.commit()

    log.info(
        "video_worker done — classified=%d duration_updated=%d",
        len(class_rows), len(duration_updates),
    )


if __name__ == "__main__":
    main()
