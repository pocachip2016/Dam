"""
M.3 CLIP text-image fallback mapper (oneshot).

텍스트 시그널이 약한 미매핑 content 자산을 대상으로
open_clip text encoder 로 콘텐츠 제목을 인코딩하고
기존 asset image embedding 과 cosine similarity 로 매핑 시도.

환경변수:
  DAM_DSN                      (필수)
  DAM_CLIP_MODEL               ViT-B-32  (기본)
  DAM_CLIP_PRETRAINED          openai    (기본)
  DAM_CLIP_THRESHOLD           0.20      (기본 — CLIP 한글 text-image 낮음)
  DAM_CLIP_BATCH               512       (asset embedding batch)
  DAM_CLIP_SKIP_CLASSIFIED     true      (composition/ui_service/draft 스킵)

실행:
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam .venv/bin/python -m ingest.clip_text_mapper
"""
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

try:
    import psycopg
    from psycopg.rows import dict_row
    from pgvector.psycopg import register_vector
except ImportError:
    sys.exit("psycopg / pgvector 미설치")

try:
    import numpy as np
except ImportError:
    sys.exit("numpy 미설치")

try:
    import torch
    import open_clip
except ImportError:
    sys.exit("torch / open_clip 미설치")

DSN        = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")
MODEL_NAME = os.environ.get("DAM_CLIP_MODEL", "ViT-B-32")
PRETRAINED = os.environ.get("DAM_CLIP_PRETRAINED", "openai")
THRESHOLD  = float(os.environ.get("DAM_CLIP_THRESHOLD", "0.20"))
BATCH      = int(os.environ.get("DAM_CLIP_BATCH", "512"))
SKIP_CLS   = os.environ.get("DAM_CLIP_SKIP_CLASSIFIED", "true").lower() != "false"

_DB_MODEL  = "clip-vit-b32"   # assets.embeddings 의 model_name 키
_SKIP_CLS  = {"composition", "ui_service", "draft"}

_UPSERT_CONTENT_EMB = """
INSERT INTO content_title_embeddings (content_id, model_name, vector, encoded_at)
VALUES (%s, %s, %s, now())
ON CONFLICT (content_id, model_name) DO UPDATE SET
  vector     = EXCLUDED.vector,
  encoded_at = now();
"""

_UPSERT_LINK = """
INSERT INTO asset_content_link
  (asset_id, content_id, confidence, method, status)
VALUES (%s, %s, %s, 'clip_similarity', 'candidate')
ON CONFLICT (asset_id, content_id) DO UPDATE SET
  confidence = GREATEST(asset_content_link.confidence, EXCLUDED.confidence),
  method     = EXCLUDED.method,
  updated_at = now();
"""


def _load_model(device: str):
    log.info("loading %s/%s on %s", MODEL_NAME, PRETRAINED, device)
    model, _, _ = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    tokenizer   = open_clip.get_tokenizer(MODEL_NAME)
    model.eval().to(device)
    return model, tokenizer


def encode_titles(model, tokenizer, titles: list[str], device: str) -> np.ndarray:
    """제목 목록 → L2-정규화된 float32 numpy array (N, 512)."""
    with torch.no_grad():
        tokens = tokenizer(titles).to(device)
        feats  = model.encode_text(tokens)
        feats  = feats / feats.norm(dim=-1, keepdim=True)
    return feats.cpu().float().numpy()


def _fetch_content_index(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT content_id, title, original_title FROM content_catalog_mirror")
        return cur.fetchall()


def _fetch_cached_content_embs(
    conn: psycopg.Connection,
) -> dict[int, np.ndarray]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT content_id, vector FROM content_title_embeddings WHERE model_name=%s",
            (_DB_MODEL,),
        )
        return {r["content_id"]: np.array(r["vector"], dtype=np.float32) for r in cur.fetchall()}


def _skip_asset_ids(conn: psycopg.Connection) -> set[int]:
    """composition/ui_service/draft 클래스 자산 ID — 매핑 스킵 대상."""
    if not SKIP_CLS:
        return set()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT asset_id FROM asset_classifications WHERE class = ANY(%s)",
            (list(_SKIP_CLS),),
        )
        return {r["asset_id"] for r in cur.fetchall()}


def _read_cursor(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM sync_cursors WHERE key='clip_text_mapper_last_id'")
        row = cur.fetchone()
        return int(row["value"]) if row else 0


def _write_cursor(conn: psycopg.Connection, value: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE sync_cursors SET value=%s, updated_at=now() WHERE key='clip_text_mapper_last_id'",
            (str(value),),
        )


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info("clip_text_mapper start — model=%s threshold=%.2f device=%s", MODEL_NAME, THRESHOLD, device)

    model, tokenizer = _load_model(device)

    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        register_vector(conn)
        # 1. 콘텐츠 인덱스 로드
        contents = _fetch_content_index(conn)
        log.info("content_index: %d items", len(contents))

        # 2. 콘텐츠 제목 임베딩 (캐시 우선)
        cached = _fetch_cached_content_embs(conn)
        to_encode = [c for c in contents if c["content_id"] not in cached]

        if to_encode:
            log.info("encoding %d content titles...", len(to_encode))
            titles = [
                (c["title"] or "") + (" " + c["original_title"] if c.get("original_title") else "")
                for c in to_encode
            ]
            vecs = encode_titles(model, tokenizer, titles, device)
            with conn.cursor() as cur:
                rows = [(c["content_id"], _DB_MODEL, v.tolist()) for c, v in zip(to_encode, vecs)]
                cur.executemany(_UPSERT_CONTENT_EMB, rows)
            conn.commit()
            for c, v in zip(to_encode, vecs):
                cached[c["content_id"]] = v
            log.info("content embeddings cached: %d total", len(cached))

        # 3. content_id 순서 고정 → 행렬
        cid_list = list(cached.keys())
        content_mat = np.stack([cached[cid] for cid in cid_list])  # (C, 512)

        # 4. 스킵 자산 ID 집합
        skip_ids = _skip_asset_ids(conn)
        log.info("skip_ids (composition/ui/draft): %d", len(skip_ids))

        last_id   = _read_cursor(conn)
        total_new = 0
        processed = 0

        while True:
            # 미매핑 content 클래스 자산 + embedding 있는 것 (cursor 기반)
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT e.asset_id, e.vector
                    FROM embeddings e
                    JOIN asset_classifications ac ON ac.asset_id = e.asset_id AND ac.class = 'content'
                    WHERE e.model_name = %s
                      AND e.asset_id > %s
                      AND NOT EXISTS (
                          SELECT 1 FROM asset_content_link acl WHERE acl.asset_id = e.asset_id
                      )
                    ORDER BY e.asset_id
                    LIMIT %s
                    """,
                    (_DB_MODEL, last_id, BATCH),
                )
                rows = cur.fetchall()

            if not rows:
                break

            # 스킵 필터
            rows = [r for r in rows if r["asset_id"] not in skip_ids]
            if not rows:
                # cursor 갱신 후 계속
                with conn.cursor() as cur:
                    _write_cursor(conn, rows[-1]["asset_id"] if rows else last_id + BATCH)
                conn.commit()
                last_id += BATCH
                continue

            # asset embedding 행렬
            asset_ids = [r["asset_id"] for r in rows]
            asset_mat = np.array([r["vector"] for r in rows], dtype=np.float32)  # (A, 512)

            # cosine similarity (A x C)
            sim = asset_mat @ content_mat.T  # (A, C)

            link_rows: list[tuple] = []
            for i, aid in enumerate(asset_ids):
                best_j   = int(np.argmax(sim[i]))
                best_sim = float(sim[i, best_j])
                if best_sim >= THRESHOLD:
                    link_rows.append((aid, cid_list[best_j], round(best_sim, 4)))
                    total_new += 1

            if link_rows:
                with conn.cursor() as cur:
                    cur.executemany(_UPSERT_LINK, link_rows)

            with conn.cursor() as cur:
                _write_cursor(conn, asset_ids[-1])
            conn.commit()

            last_id   = asset_ids[-1]
            processed += len(rows)
            log.info("processed %d assets (last_id=%d) new_links=%d", processed, last_id, total_new)

    log.info("clip_text_mapper done — processed=%d new_links=%d", processed, total_new)


if __name__ == "__main__":
    main()
