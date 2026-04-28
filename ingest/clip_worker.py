import os

from typing import Optional

import logging

import psycopg2

from PIL import Image

import torch

from torchvision import transforms

from open_clip_torch import create_model, transform_image



# Environment variables

MODEL = os.getenv('MODEL', 'open_clip')

MODEL_NAME = os.getenv('MODEL_NAME', 'clip-vit-b32' if MODEL == 'open_clip' else 'cn-clip-vitb16')

BATCH = int(os.getenv('BATCH', 128))

WORKERS = int(os.getenv('WORKERS', 4))

THUMB_DIR = os.getenv('THUMB_DIR', '~/Work/Dam/dam_data/thumbnails')

DAM_DSN = os.getenv('DAM_DSN')

MODEL_CACHE_DIR = os.getenv('MODEL_CACHE_DIR', '~/Work/Dam/dam_data/models')



# Initialize logging

logging.basicConfig(level=logging.WARNING)

logger = logging.getLogger(__name__)



def main():

    conn = psycopg2.connect(DAM_DSN)

    try:

        dispatch_model(conn)

    finally:

        conn.close()



def dispatch_model(conn):

    if MODEL == 'open_clip':

        model, preprocess = create_model('ViT-B/32', pretrained='laion2b')

    elif MODEL == 'cn_clip':

        model, preprocess = create_model('ViT-B/16', pretrained='cn-clip-vitb16')

    else:

        raise ValueError(f"Unsupported model: {MODEL}")



    # Load thumbnails

    thumbs = fetch_pending(conn)

    encode_and_insert(thumbs, conn, model, preprocess)



def fetch_pending(conn):

    with conn.cursor() as cur:

        cur.execute("""

            SELECT a.asset_id, a.thumbnail_path

            FROM assets a

            LEFT JOIN embeddings e ON e.asset_id = a.asset_id AND e.model_name = %s

            WHERE e.asset_id IS NULL AND a.thumbnail_path IS NOT NULL

        """, (MODEL_NAME,))

        return cur.fetchall()



def encode_and_insert(thumbs, conn, model, preprocess):

    transform = transforms.Compose([

        transforms.Resize((256, 256)),

        transforms.ToTensor(),

        preprocess

    ])



    for i in range(0, len(thumbs), BATCH):

        batch = thumbs[i:i+BATCH]

        images = [Image.open(os.path.join(THUMB_DIR, thumb_path)).convert('RGB') for asset_id, thumb_path in batch]

        inputs = torch.stack([transform(img) for img in images]).to('cuda')

        with torch.no_grad():

            outputs = model.encode_image(inputs).cpu().numpy().astype('float32')



        write_hashes(conn, [(asset_id, MODEL_NAME, embedding) for asset_id, _, embedding in zip(*batch, outputs)])



def write_hashes(conn, results):

    with conn.cursor() as cur:

        placeholders = ', '.join(['%s'] * len(results))

        columns = 'asset_id, model_name, embedding'

        query = f"INSERT INTO embeddings ({columns}) VALUES {placeholders} ON CONFLICT (asset_id, model_name) DO NOTHING"

        cur.executemany(query, results)

        conn.commit()



if __name__ == "__main__":

    main()
