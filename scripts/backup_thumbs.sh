#!/usr/bin/env bash
# Thumbnail + model rsync backup.
# Usage: bash scripts/backup_thumbs.sh
#   env: THUMB_SRC (default dam_data/thumbnails)
#        THUMB_DST (default data/thumb_backup)
#        MODEL_SRC (default dam_data/models)
#        MODEL_DST (default data/model_backup)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

THUMB_SRC="${THUMB_SRC:-$PROJECT_ROOT/dam_data/thumbnails}"
THUMB_DST="${THUMB_DST:-$PROJECT_ROOT/data/thumb_backup}"
MODEL_SRC="${MODEL_SRC:-$PROJECT_ROOT/dam_data/models}"
MODEL_DST="${MODEL_DST:-$PROJECT_ROOT/data/model_backup}"

LOG_FILE="${THUMB_DST}/backup_thumbs.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$THUMB_DST" "$MODEL_DST"

# ── 썸네일 rsync (소스가 truth — --delete로 삭제분도 반영) ──────────────
if [ -d "$THUMB_SRC" ]; then
    log "thumb sync start: $THUMB_SRC → $THUMB_DST"
    rsync -a --delete --stats "$THUMB_SRC/" "$THUMB_DST/" 2>>"$LOG_FILE" | \
        grep -E "Number of files|transferred|speedup" | while read -r line; do log "$line"; done
    THUMB_COUNT=$(find "$THUMB_DST" -type f | wc -l)
    log "thumb sync done: ${THUMB_COUNT} files in dst"
else
    log "WARN: THUMB_SRC not found ($THUMB_SRC) — skipping"
fi

# ── 모델 rsync (변경 드물므로 --ignore-existing) ──────────────────────────
if [ -d "$MODEL_SRC" ]; then
    log "model backup start: $MODEL_SRC → $MODEL_DST"
    rsync -a --ignore-existing --stats "$MODEL_SRC/" "$MODEL_DST/" 2>>"$LOG_FILE" | \
        grep -E "Number of files|transferred" | while read -r line; do log "$line"; done
    log "model backup done"
else
    log "WARN: MODEL_SRC not found ($MODEL_SRC) — skipping"
fi

log "backup_thumbs complete"
