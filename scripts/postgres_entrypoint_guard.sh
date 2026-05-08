#!/usr/bin/env bash
# Entrypoint wrapper for dam_postgres — prevents silent re-initialization.
# Replaces the default entrypoint in docker-compose.yml.
#
# Behavior:
#   PG_VERSION present  → pass through to upstream entrypoint (normal start)
#   PG_VERSION absent + DAM_ALLOW_INIT=yes → pass through (intentional fresh init)
#   PG_VERSION absent + no flag           → print error and exit 1
set -euo pipefail

DATA_DIR="/var/lib/postgresql/data"
UPSTREAM="/usr/local/bin/docker-entrypoint.sh"

if [ -f "${DATA_DIR}/PG_VERSION" ]; then
  exec "$UPSTREAM" "$@"
fi

if [ "${DAM_ALLOW_INIT:-}" = "yes" ]; then
  echo "[dam-guard] WARNING: pg_data is empty — starting fresh init because DAM_ALLOW_INIT=yes"
  exec "$UPSTREAM" "$@"
fi

cat >&2 <<'EOF'

╔══════════════════════════════════════════════════════════════════╗
║  ⛔  dam_postgres STARTUP BLOCKED — DATA DIRECTORY IS EMPTY     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  PG_VERSION not found in /var/lib/postgresql/data               ║
║  Refusing to auto-initialize a new empty cluster, which would   ║
║  silently destroy any existing data (see 2026-05-07 incident).  ║
║                                                                  ║
║  If you have a backup, restore it first:                        ║
║    docker exec -i dam_postgres pg_restore -U dam -d dam \       ║
║      < data/backups/<latest>.dump                               ║
║                                                                  ║
║  To intentionally start a FRESH cluster (data will be lost):   ║
║    DAM_ALLOW_INIT=yes docker compose up -d dam_postgres         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

EOF
exit 1
