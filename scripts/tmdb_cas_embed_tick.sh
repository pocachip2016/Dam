#!/usr/bin/env bash
# tmdb_cas realm 신규 이미지 썸네일+CLIP(2모델) 임베딩 tick.
# mediaX tmdb_backfill_orchestrator(매일 08:30 KST)가 채우는 신규 tmdb_cas asset을
# 대상으로 한다. 각 워커는 처리 대상 0개면 즉시 종료하므로 매일 실행해도 비용 미미.
# Usage: bash scripts/tmdb_cas_embed_tick.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

THUMB_REALM=tmdb_cas \
  SRC_REMAP=/dam_tmdb_cas=/mnt/d/dam_data/tmdb \
  THUMB_DIR="$PROJECT_ROOT/dam_data/thumbnails" \
  .venv/bin/python ingest/thumbnail_worker.py

MODEL=open_clip .venv/bin/python ingest/clip_worker.py
MODEL=cn_clip   .venv/bin/python ingest/clip_worker.py
