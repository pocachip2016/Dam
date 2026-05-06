#!/usr/bin/env python3
"""Phase 3.6 OCR worker — EasyOCR (GPU) + pytesseract fallback

실행:
  # Smoke 1000건
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam DAM_BATCH=64 SMOKE=1000 \
    .venv/bin/python ingest/ocr_worker.py > dam_data/poc_ocr_smoke.log 2>&1 &

  # 전체 배치 (야간)
  DAM_DSN=postgresql://dam:dam@localhost:15432/dam DAM_BATCH=64 \
    .venv/bin/python ingest/ocr_worker.py > dam_data/poc_ocr_full.log 2>&1 &
"""

import os
import sys
import logging
import time
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

try:
    import psycopg
except ImportError:
    sys.exit("psycopg 미설치")

try:
    from langdetect import detect, LangDetectException
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False
    log.warning("langdetect 미설치 — ocr_lang=None")

DSN   = os.environ.get("DAM_DSN",   "postgresql://dam:dam@localhost:15432/dam")
BATCH = int(os.environ.get("DAM_BATCH", "64"))
SMOKE = int(os.environ.get("SMOKE",     "0"))   # 0 = 제한 없음
REALM = os.environ.get("DAM_REALM",  "poc_sample")
MIN_CONF = float(os.environ.get("OCR_MIN_CONF", "0.3"))

# EasyOCR lazy singleton
_reader = None


def get_reader():
    global _reader
    if _reader is None:
        try:
            import torch
            import easyocr
            use_gpu = torch.cuda.is_available()
            _reader = easyocr.Reader(['ko', 'en'], gpu=use_gpu, verbose=False)
            log.info(f"EasyOCR 초기화 완료 (gpu={use_gpu})")
        except Exception as e:
            log.warning(f"EasyOCR 초기화 실패: {e}")
            _reader = None
    return _reader


def ocr_with_easyocr(img_path: str) -> str | None:
    reader = get_reader()
    if not reader:
        return None
    try:
        result = reader.readtext(img_path)
        texts = [r[1] for r in result if r[2] >= MIN_CONF]
        return ' '.join(texts)
    except Exception as e:
        log.debug(f"EasyOCR 오류 ({img_path}): {e}")
        return None


def ocr_with_tesseract(img_path: str) -> str | None:
    try:
        import pytesseract
        text = pytesseract.image_to_string(img_path, lang='kor+eng')
        return text.strip()
    except Exception as e:
        log.debug(f"Tesseract 오류 ({img_path}): {e}")
        return None


def detect_lang(text: str) -> str:
    if not text or not HAS_LANGDETECT:
        return 'none' if not text else 'unknown'
    try:
        lang = detect(text)
        if lang == 'ko':
            return 'ko'
        elif lang in ('en', 'und'):
            return 'en'
        else:
            has_ko = bool(re.search(r'[가-힣]', text))
            has_en = bool(re.search(r'[A-Za-z]', text))
            if has_ko and has_en:
                return 'mixed'
            return 'ko' if has_ko else 'en'
    except LangDetectException:
        has_ko = bool(re.search(r'[가-힣]', text))
        return 'ko' if has_ko else 'none'


def compress_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def run_ocr(thumb_path: str) -> tuple[str, str]:
    """Returns (ocr_text, ocr_lang). Empty string = processed but no text."""
    text = ocr_with_easyocr(thumb_path)
    if text is None:
        text = ocr_with_tesseract(thumb_path)
    if text is None:
        text = ''
    text = compress_whitespace(text)
    lang = detect_lang(text)
    return text, lang


def fetch_batch(conn, limit: int) -> list[tuple[int, str]]:
    rows = conn.execute(
        """
        SELECT a.id, a.thumbnail_path
        FROM assets a
        JOIN asset_storage s ON s.asset_id = a.id
        WHERE s.realm = %(realm)s
          AND a.thumbnail_path IS NOT NULL
          AND a.ocr_done_at IS NULL
          AND a.primary_ext IN ('.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff')
        ORDER BY ('poster' = ANY(a.role_hint) OR 'banner' = ANY(a.role_hint)) DESC, a.id
        LIMIT %(limit)s
        """,
        {'realm': REALM, 'limit': limit},
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def write_batch(conn, results: list[tuple[int, str, str]]):
    with conn.cursor() as cur:
        cur.executemany(
            """
            UPDATE assets SET
              ocr_text    = %(text)s,
              ocr_lang    = %(lang)s,
              ocr_done_at = now()
            WHERE id = %(aid)s
            """,
            [{'aid': aid, 'text': text, 'lang': lang} for aid, text, lang in results],
        )
    conn.commit()


def run():
    t0 = time.time()
    with psycopg.connect(DSN) as conn:
        total_img = conn.execute(
            """
            SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id
            WHERE s.realm = %s AND a.thumbnail_path IS NOT NULL
              AND a.primary_ext IN ('.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff')
            """,
            (REALM,),
        ).fetchone()[0]
        log.info(f"대상 이미지 총 {total_img:,}건, BATCH={BATCH}, SMOKE={SMOKE or '전체'}")

        processed = errors = 0
        smoke_limit = SMOKE if SMOKE > 0 else float('inf')

        while processed < smoke_limit:
            fetch_n = BATCH if SMOKE == 0 else min(BATCH, SMOKE - processed)
            rows = fetch_batch(conn, fetch_n)
            if not rows:
                break

            results = []
            for aid, thumb_path in rows:
                if not os.path.isfile(thumb_path):
                    results.append((aid, '', 'none'))
                    errors += 1
                    continue
                try:
                    text, lang = run_ocr(thumb_path)
                    results.append((aid, text, lang))
                except Exception as e:
                    log.warning(f"OCR 오류 asset {aid}: {e}")
                    results.append((aid, '', 'none'))
                    errors += 1

            write_batch(conn, results)
            processed += len(rows)

            elapsed = time.time() - t0
            rate = processed / elapsed if elapsed > 0 else 0
            remain = total_img - processed if SMOKE == 0 else max(0, SMOKE - processed)
            eta_min = remain / rate / 60 if rate > 0 else 0
            log.info(
                f"[{processed:,}/{total_img:,}] errors={errors} "
                f"rate={rate:.0f}/s eta={eta_min:.1f}min"
            )

        elapsed = time.time() - t0
        log.info(f"완료: {processed:,}건, errors={errors}, elapsed={elapsed:.0f}s")


if __name__ == "__main__":
    run()
