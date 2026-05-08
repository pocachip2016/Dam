#!/usr/bin/env bash
# Daily pg_dump backup with N-day rotation.
# Usage: bash scripts/db_backup.sh
#   env: RETENTION_DAYS (default 7), BACKUP_DIR (default ./data/backups)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/data/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
CONTAINER="${CONTAINER:-dam_postgres}"
DB_USER="${DB_USER:-dam}"
DB_NAME="${DB_NAME:-dam}"

mkdir -p "$BACKUP_DIR"
LOG_FILE="$BACKUP_DIR/backup.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}\$"; then
  log "ERROR: container '${CONTAINER}' not running — abort"
  exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/dam_${TIMESTAMP}.dump"

log "backup start → $(basename "$BACKUP_FILE")"

if docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -Z 9 > "$BACKUP_FILE" 2>>"$LOG_FILE"; then
  SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  log "backup complete → $SIZE"
else
  log "ERROR: pg_dump failed — removing partial file"
  rm -f "$BACKUP_FILE"
  exit 1
fi

DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -name 'dam_*.dump' -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
  log "rotated: deleted ${DELETED} backup(s) older than ${RETENTION_DAYS}d"
fi

COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -name 'dam_*.dump' | wc -l)
TOTAL=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
log "summary: ${COUNT} backups kept, total ${TOTAL}"
