"""
M.2 asset classification + content mapping oneshot worker.

환경변수:
  DAM_DSN                    (필수)
  DAM_MAPPING_THRESHOLD      float, default 0.85
  DAM_MAPPING_BATCH          int,   default 1000
  DAM_FUZZY_RATIO            float, default 0.88
  DAM_SKIP_NON_CONTENT_MAPPING bool, default true

실행:
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam .venv/bin/python -m ingest.asset_mapper
"""
import logging
import os
import sys
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    sys.exit("psycopg 미설치")

try:
    from rapidfuzz import fuzz
except ImportError:
    sys.exit("rapidfuzz 미설치. 실행: pip install rapidfuzz")

from ._classification_rules import FOLDER_PATTERNS, FILENAME_KEYWORDS
from ._korean_norm import extract_korean, normalize_title

DSN       = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")
THRESHOLD = float(os.environ.get("DAM_MAPPING_THRESHOLD", "0.85"))
BATCH     = int(os.environ.get("DAM_MAPPING_BATCH", "1000"))
FUZZY_R   = float(os.environ.get("DAM_FUZZY_RATIO", "0.88"))
SKIP_NON  = os.environ.get("DAM_SKIP_NON_CONTENT_MAPPING", "true").lower() != "false"

_SKIP_CLASSES = {"composition", "ui_service", "draft"}

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

_UPSERT_LINK = """
INSERT INTO asset_content_link
  (asset_id, content_id, confidence, method, status)
VALUES (%s, %s, %s, %s, 'candidate')
ON CONFLICT (asset_id, content_id) DO UPDATE SET
  confidence = GREATEST(asset_content_link.confidence, EXCLUDED.confidence),
  method     = EXCLUDED.method,
  updated_at = now();
"""


@dataclass
class Classification:
    cls: str
    sub_class: str | None
    confidence: float
    method: str
    signal: str


@dataclass
class ContentMatch:
    content_id: int
    confidence: float
    method: str


def classify_asset(asset_row: dict, tags: list[str]) -> list[Classification]:
    results: list[Classification] = []
    seen: set[str] = set()

    folder_path = asset_row.get("folder_path") or ""
    filename    = asset_row.get("filename") or ""
    role_hint   = asset_row.get("role_hint") or []

    # 1. 폴더 패턴 매칭
    for pattern, cls, sub_cls, conf in FOLDER_PATTERNS:
        if pattern.search(folder_path):
            if cls not in seen:
                results.append(Classification(cls, sub_cls, conf, "folder_pattern", pattern.pattern))
                seen.add(cls)

    # 2. filename 키워드 매칭
    fn_lower = filename.lower()
    for cls, keywords in FILENAME_KEYWORDS.items():
        if cls not in seen:
            for kw in keywords:
                if kw.lower() in fn_lower:
                    results.append(Classification(cls, None, 0.88, "filename_keyword", kw))
                    seen.add(cls)
                    break

    # 3. role_hint=['logo'] → branding
    if isinstance(role_hint, list) and "logo" in role_hint and "branding" not in seen:
        results.append(Classification("branding", None, 0.90, "role_hint", "logo"))
        seen.add("branding")

    return results


def _year_bonus(row: dict, content: dict) -> float:
    year_hint = row.get("year_hint")
    prod_year = content.get("production_year")
    if not year_hint or not prod_year:
        return 0.0
    diff = abs(int(year_hint) - int(prod_year))
    if diff == 0:
        return 0.05
    if diff == 1:
        return 0.02
    return 0.0


def match_content(
    asset_row: dict,
    tags: list[str],
    ocr_text: str | None,
    content_index: list[dict],
) -> list[ContentMatch]:
    """4축 시그널로 content_catalog_mirror 에서 매핑 후보 반환."""
    filename = asset_row.get("filename") or ""
    folder_path = asset_row.get("folder_path") or ""

    fn_korean = extract_korean(filename)
    folder_korean = extract_korean(folder_path)

    matches: list[ContentMatch] = []

    for content in content_index:
        cid = content["content_id"]
        title = content.get("title") or ""
        orig  = content.get("original_title") or ""
        norm_title = normalize_title(title)
        norm_orig  = normalize_title(orig)

        best_score = 0.0
        best_method = "filename"

        # tag 시그널 (최고 우선)
        for tag in tags:
            if normalize_title(tag) in norm_title or normalize_title(tag) in norm_orig:
                best_score = max(best_score, 0.97)
                best_method = "tag"
                break

        # filename 한글 substring 매핑
        for tok in fn_korean:
            if len(tok) < 2:
                continue
            norm_tok = normalize_title(tok)
            if norm_tok in norm_title or norm_tok in norm_orig:
                score = min(0.98, 0.85 + len(tok) * 0.01)
                if score > best_score:
                    best_score = score
                    best_method = "filename"
            else:
                ratio = fuzz.ratio(norm_tok, norm_title) / 100
                if ratio >= FUZZY_R and ratio > best_score:
                    best_score = ratio
                    best_method = "filename"

        # folder_path 한글
        for tok in folder_korean:
            if len(tok) < 2:
                continue
            norm_tok = normalize_title(tok)
            if norm_tok in norm_title or norm_tok in norm_orig:
                score = 0.88
                if score > best_score:
                    best_score = score
                    best_method = "folder_path"

        # ocr_text
        if ocr_text:
            for tok in extract_korean(ocr_text):
                if len(tok) < 2:
                    continue
                norm_tok = normalize_title(tok)
                if norm_tok in norm_title or norm_tok in norm_orig:
                    score = min(0.92, 0.85 + len(tok) * 0.01)
                    if score > best_score:
                        best_score = score
                        best_method = "ocr_text"
                else:
                    ratio = fuzz.ratio(norm_tok, norm_title) / 100
                    if ratio >= FUZZY_R and ratio > best_score:
                        best_score = ratio
                        best_method = "ocr_text"

        best_score += _year_bonus(asset_row, content)
        best_score = min(1.0, best_score)

        if best_score >= THRESHOLD:
            matches.append(ContentMatch(cid, round(best_score, 4), best_method))

    return sorted(matches, key=lambda m: -m.confidence)


def _read_cursor(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM sync_cursors WHERE key='asset_mapper_last_id'")
        row = cur.fetchone()
        return int(row["value"]) if row else 0


def _write_cursor(conn: psycopg.Connection, value: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE sync_cursors SET value=%s, updated_at=now() WHERE key='asset_mapper_last_id'",
            (str(value),),
        )


def _fetch_content_index(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT content_id, title, original_title, production_year FROM content_catalog_mirror")
        return cur.fetchall()


def _fetch_tags(conn: psycopg.Connection, asset_ids: list[int]) -> dict[int, list[str]]:
    if not asset_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT at.asset_id, t.name FROM asset_tags at JOIN tags t ON t.id=at.tag_id WHERE at.asset_id = ANY(%s)",
            (asset_ids,),
        )
        result: dict[int, list[str]] = {}
        for row in cur.fetchall():
            result.setdefault(row["asset_id"], []).append(row["name"])
    return result


def main() -> None:
    log.info("asset_mapper start — threshold=%.2f batch=%d", THRESHOLD, BATCH)

    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        last_id = _read_cursor(conn)
        log.info("cursor: last_id=%d", last_id)

        content_index = _fetch_content_index(conn)
        log.info("content_index: %d items", len(content_index))

        total_classified = 0
        total_mapped = 0
        processed = 0

        while True:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT a.id, a.filename,
                           COALESCE(s.top_folder || '/' || s.sub_folder, '') AS folder_path,
                           a.role_hint, a.year_hint, a.ocr_text
                    FROM assets a
                    LEFT JOIN asset_storage s ON s.asset_id = a.id AND s.is_authoritative = true
                    WHERE a.id > %s
                    ORDER BY a.id
                    LIMIT %s
                    """,
                    (last_id, BATCH),
                )
                rows = cur.fetchall()

            if not rows:
                break

            asset_ids = [r["id"] for r in rows]
            tags_map  = _fetch_tags(conn, asset_ids)

            class_rows: list[tuple] = []
            link_rows:  list[tuple] = []

            for row in rows:
                aid  = row["id"]
                tags = tags_map.get(aid, [])
                ocr  = row.get("ocr_text")

                classes = classify_asset(row, tags)
                if not classes:
                    classes = [Classification("unclassified", None, 1.0, "rule", "no_signal")]

                for c in classes:
                    class_rows.append((aid, c.cls, c.sub_class, c.confidence, c.method, c.signal))

                total_classified += 1

                # 콘텐츠 매핑 시도 여부 판단
                class_names = {c.cls for c in classes}
                role_hint   = row.get("role_hint") or []
                want_map = (
                    "content" in class_names
                    or (isinstance(role_hint, list) and any(r in role_hint for r in ("poster", "banner", "detail")))
                )
                skip_map = SKIP_NON and class_names.issubset(_SKIP_CLASSES | {"unclassified"})

                if want_map and not skip_map:
                    content_matches = match_content(row, tags, ocr, content_index)
                    for m in content_matches:
                        link_rows.append((aid, m.content_id, m.confidence, m.method))
                        # 매핑 성공 시 content 클래스 보강
                        if "content" not in class_names:
                            class_rows.append((aid, "content", None, m.confidence, "rule", "matched_content"))
                            class_names.add("content")
                    if content_matches:
                        total_mapped += 1

            with conn.cursor() as cur:
                if class_rows:
                    cur.executemany(_UPSERT_CLASS, class_rows)
                if link_rows:
                    cur.executemany(_UPSERT_LINK, link_rows)
                _write_cursor(conn, rows[-1]["id"])
            conn.commit()

            last_id = rows[-1]["id"]
            processed += len(rows)
            log.info("processed %d assets (last_id=%d) classified=%d mapped=%d",
                     processed, last_id, total_classified, total_mapped)

    log.info("asset_mapper done — processed=%d classified=%d mapped=%d",
             processed, total_classified, total_mapped)


if __name__ == "__main__":
    main()
