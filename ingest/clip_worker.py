#!/usr/bin/env python3
import os
import sys
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

try:
    import psycopg
    import torch
    from torch.utils.data import Dataset, DataLoader
    from PIL import Image, UnidentifiedImageError
except ImportError as e:
    sys.exit(f'의존성 미설치: {e}')

MODEL = os.environ.get('MODEL', 'open_clip')
MODEL_NAME = os.environ.get('MODEL_NAME',
    'clip-vit-b32' if MODEL == 'open_clip' else 'cn-clip-vitb16')
BATCH = int(os.environ.get('BATCH', 128))
WORKERS = int(os.environ.get('WORKERS', 4))
LIMIT = int(os.environ.get('LIMIT', 0))
THUMB_DIR = os.environ.get('THUMB_DIR',
    str(Path.home() / 'Work/Dam/dam_data/thumbnails'))
DAM_DSN = os.environ.get('DAM_DSN', 'postgresql://dam:dam@localhost:15432/dam')
MODEL_CACHE_DIR = os.environ.get('MODEL_CACHE_DIR',
    str(Path.home() / 'Work/Dam/dam_data/models'))


def load_model(device):
    os.environ.setdefault('HF_HUB_CACHE', MODEL_CACHE_DIR)
    os.environ.setdefault('TORCH_HOME', MODEL_CACHE_DIR)

    if MODEL == 'open_clip':
        import open_clip
        model, _, preprocess = open_clip.create_model_and_transforms(
            'ViT-B-32', pretrained='laion2b_s34b_b79k')
        model = model.to(device).eval()
        return model, preprocess

    elif MODEL == 'cn_clip':
        import cn_clip.clip as clip
        model, preprocess = clip.load_from_name(
            'ViT-B-16', device=device, download_root=MODEL_CACHE_DIR)
        model.eval()
        return model, preprocess

    else:
        raise ValueError(f'Unknown MODEL={MODEL!r} — 지원: open_clip, cn_clip')


def fetch_pending(conn) -> list:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT a.id, a.thumbnail_path
            FROM assets a
            LEFT JOIN embeddings e
                ON e.asset_id = a.id AND e.model_name = %s
            WHERE a.thumbnail_path IS NOT NULL
              AND e.asset_id IS NULL
            ORDER BY a.id
        """, (MODEL_NAME,))
        rows = cur.fetchall()
    return rows[:LIMIT] if LIMIT else rows


class ThumbDataset(Dataset):
    def __init__(self, rows, preprocess):
        self.rows = rows
        self.preprocess = preprocess

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        asset_id, thumb_path = self.rows[idx]
        try:
            img = self.preprocess(Image.open(thumb_path).convert('RGB'))
            return asset_id, img, True
        except (UnidentifiedImageError, OSError, Exception):
            return asset_id, torch.zeros(3, 224, 224), False


def collate_fn(batch):
    ids = [b[0] for b in batch]
    imgs = torch.stack([b[1] for b in batch])
    oks = [b[2] for b in batch]
    return ids, imgs, oks


def encode_batch(model, imgs, device):
    with torch.no_grad():
        feats = model.encode_image(imgs.to(device))
        feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.cpu().float().numpy()


def insert_embeddings(conn, asset_ids, vectors):
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO embeddings (asset_id, model_name, vector)
            VALUES (%s, %s, %s::vector)
            ON CONFLICT (asset_id, model_name) DO NOTHING
            """,
            [(aid, MODEL_NAME, '[' + ','.join(map(str, vec.tolist())) + ']')
             for aid, vec in zip(asset_ids, vectors)]
        )
    conn.commit()


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    log.info(f'device={device} MODEL={MODEL} MODEL_NAME={MODEL_NAME} BATCH={BATCH}')

    model, preprocess = load_model(device)

    with psycopg.connect(DAM_DSN) as conn:
        rows = fetch_pending(conn)
        log.info(f'처리 대상: {len(rows):,}개')
        if not rows:
            log.info('처리할 임베딩 없음')
            return

        dataset = ThumbDataset(rows, preprocess)
        loader = DataLoader(
            dataset,
            batch_size=BATCH,
            num_workers=WORKERS,
            collate_fn=collate_fn,
            multiprocessing_context='spawn' if WORKERS > 0 else None,
            persistent_workers=WORKERS > 0,
        )

        ok = err = batch_count = 0
        t0 = time.time()

        for asset_ids, imgs, oks in loader:
            ok_mask = torch.tensor(oks)
            valid_ids = [aid for aid, o in zip(asset_ids, oks) if o]
            err += sum(1 for o in oks if not o)

            if not valid_ids:
                continue

            valid_imgs = imgs[ok_mask]
            try:
                vectors = encode_batch(model, valid_imgs, device)
            except torch.cuda.OutOfMemoryError:
                log.warning(f'GPU OOM (batch={len(valid_ids)}), 절반으로 재시도')
                torch.cuda.empty_cache()
                half = len(valid_ids) // 2
                import numpy as np
                vectors = np.concatenate([
                    encode_batch(model, valid_imgs[:half], device),
                    encode_batch(model, valid_imgs[half:], device),
                ])

            insert_embeddings(conn, valid_ids, vectors)
            ok += len(valid_ids)
            batch_count += 1

            if batch_count % 100 == 0:
                elapsed = time.time() - t0
                rate = ok / elapsed if elapsed else 0
                log.info(f'배치 {batch_count} | ok={ok:,} err={err} ({rate:.1f}/s)')

        elapsed = time.time() - t0
        log.info(f'완료 | ok={ok:,} err={err} ({elapsed:.1f}s)')


if __name__ == '__main__':
    main()
