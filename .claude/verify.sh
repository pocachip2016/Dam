#!/usr/bin/env bash
# Dam project verify.sh — /verify <step-id> 의 진입점
# 각 step 이 자기 case 를 추가한다.
set -euo pipefail

STEP="${1:-}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DSN="${DAM_DSN:-postgresql://dam:dam@localhost:15432/dam}"

pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
psql_q() { docker exec dam_postgres psql -U dam -d dam -tAc "$1" 2>/dev/null; }

case "$STEP" in
  1.1)
    branch=$(git -C "$REPO" rev-parse --abbrev-ref HEAD)
    [[ "$branch" == "feature/server-migration" ]] \
      || fail "branch=$branch (expected feature/server-migration)"
    test -x "$REPO/.claude/verify.sh" \
      || fail "verify.sh not executable"
    test -f "$REPO/plans/dev-server-migration/index.json" \
      || fail "index.json missing"
    pass "step 1.1 branch-setup"
    ;;

  1.2)
    test -f "$REPO/.gitignore" \
      || fail ".gitignore missing"
    [[ -f "$REPO/Q1.md" ]] && fail "Q1.md still in root" || true
    [[ -f "$REPO/NEXT.md" ]] && fail "NEXT.md still in root" || true
    ls "$REPO"/scan_anal*.md 2>/dev/null && fail "scan_anal*.md still in root" || true
    test -f "$REPO/docs/initial-review.md" \
      || fail "docs/initial-review.md missing"
    test -f "$REPO/docs/scan-analysis-1.md" \
      || fail "docs/scan-analysis-1.md missing"
    if git -C "$REPO" ls-files | grep -q "__pycache__"; then
      fail "__pycache__ still tracked in git"
    fi
    grep -q "Phase 2" "$REPO/TODO.md" 2>/dev/null \
      || fail "TODO.md does not mention Phase 2"
    pass "step 1.2 harness-align"
    ;;

  1.3)
    (cd "$REPO" && docker compose config -q 2>/dev/null) \
      || fail "docker compose config failed"
    "$REPO/.venv/bin/python" -c "import fastapi, psycopg, PIL, uvicorn" 2>/dev/null \
      || fail "python imports failed — run: pip install -r requirements.txt"
    test -d /home/ktalpha/dam_data/pg_data \
      || fail "/home/ktalpha/dam_data/pg_data missing"
    pass "step 1.3 env-prepare"
    ;;

  1.4)
    healthy=$(docker inspect dam_postgres --format '{{.State.Health.Status}}' 2>/dev/null || echo "missing")
    [[ "$healthy" == "healthy" ]] || fail "dam_postgres not healthy (status=$healthy)"
    table_count=$(psql_q "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
    [[ "${table_count:-0}" -ge 6 ]] || fail "table_count=$table_count (need ≥6)"
    ext=$(psql_q "SELECT extname FROM pg_extension WHERE extname='vector'" || echo "")
    [[ "$ext" == "vector" ]] || fail "pgvector extension not installed"
    pass "step 1.4 infra-up"
    ;;

  1.5)
    mountpoint -q /mnt/designfs \
      || fail "/mnt/designfs is not mounted (DESIGNFS share)"
    mountpoint -q /mnt/designfs1 \
      || fail "/mnt/designfs1 is not mounted (DESIGNFS1 share)"
    test -d "/mnt/designfs/디자인파트/11.NEXT_UI_2022_10월오픈" \
      || fail "/mnt/designfs/디자인파트/11.NEXT_UI_2022_10월오픈 not accessible"
    test -d /mnt/d/Work/dam_poc_sample \
      || fail "/mnt/d/Work/dam_poc_sample (poc_sample target) missing"
    sample_files=$(find /mnt/d/Work/dam_poc_sample -type f 2>/dev/null | wc -l)
    [[ "${sample_files:-0}" -ge 80000 ]] \
      || fail "poc_sample file count=$sample_files (need ≥80000)"
    pass "step 1.5 nas-mount"
    ;;

  1.6)
    asset_count=$(psql_q "SELECT COUNT(*) FROM asset_storage WHERE realm='poc_sample'" || echo 0)
    [[ "${asset_count:-0}" -ge 80000 ]] \
      || fail "asset_count=$asset_count (need ≥80000)"
    thumb_count=$(psql_q "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id WHERE s.realm='poc_sample' AND a.thumbnail_path IS NOT NULL" || echo 0)
    [[ "${thumb_count:-0}" -ge 79000 ]] \
      || fail "thumb_count=$thumb_count (need ≥79000)"
    pass "step 1.6 data-load"
    ;;

  1.7)
    http_code=$(curl -o /dev/null -s -w "%{http_code}" http://localhost:18000/stats)
    [[ "$http_code" == "200" ]] || fail "/stats returned HTTP $http_code"
    body=$(curl -fsS "http://localhost:18000/search?q=.jpg&realm=poc_sample&limit=5")
    echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('total',0)>=1, 'no hits'" \
      || fail "/search returned no hits"
    pass "step 1.7 api-smoke"
    ;;

  2.1)
    "$REPO/.venv/bin/python" -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" \
      || fail "torch.cuda.is_available() == False"
    "$REPO/.venv/bin/python" -c "import open_clip" 2>/dev/null \
      || fail "open_clip import failed"
    "$REPO/.venv/bin/python" -c "import cn_clip" 2>/dev/null \
      || fail "cn_clip import failed"
    test -d "$REPO/dam_data/models" \
      || fail "dam_data/models not created"
    pass "step 2.1 env-prepare-gpu"
    ;;

  2.2)
    test -f "$REPO/ingest/clip_worker.py" \
      || fail "ingest/clip_worker.py missing"
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "from ingest.clip_worker import main" 2>/dev/null \
      || fail "ingest.clip_worker.main not importable"
    smoke=$(psql_q "SELECT COUNT(*) FROM embeddings WHERE model_name='clip-vit-b32'")
    [[ "${smoke:-0}" -ge 1000 ]] || fail "smoke embeddings count=$smoke (need ≥1000)"
    pass "step 2.2 worker-impl"
    ;;

  2.3)
    cnt=$(psql_q "SELECT COUNT(*) FROM embeddings WHERE model_name='clip-vit-b32'")
    [[ "${cnt:-0}" -ge 159500 ]] \
      || fail "open_clip embeddings count=$cnt (need ≥159500)"
    pass "step 2.3 open-embed-full"
    ;;

  2.4)
    cnt=$(psql_q "SELECT COUNT(*) FROM embeddings WHERE model_name='cn-clip-vitb16'")
    [[ "${cnt:-0}" -ge 159500 ]] \
      || fail "cn_clip embeddings count=$cnt (need ≥159500)"
    open_cnt=$(psql_q "SELECT COUNT(*) FROM embeddings WHERE model_name='clip-vit-b32'")
    [[ "${open_cnt:-0}" -ge 159500 ]] \
      || fail "open_clip embeddings missing (count=$open_cnt) — coexistence broken"
    pass "step 2.4 cn-embed-full"
    ;;

  2.5)
    http_open=$(curl -o /dev/null -s -w "%{http_code}" "http://localhost:18000/search_text?q=blue&model=clip-vit-b32&limit=5")
    [[ "$http_open" == "200" ]] || fail "/search_text (open) returned HTTP $http_open"
    http_cn=$(curl -o /dev/null -s -w "%{http_code}" "http://localhost:18000/search_text?q=강아지&model=cn-clip-vitb16&limit=5")
    [[ "$http_cn" == "200" ]] || fail "/search_text (cn) returned HTTP $http_cn"
    pass "step 2.5 text-search-api"
    ;;

  2.6)
    test -f "$REPO/docs/clip-comparison.md" \
      || fail "docs/clip-comparison.md missing"
    grep -q "ADR-" "$REPO/docs/ADR.md" 2>/dev/null \
      || fail "docs/ADR.md missing CLIP model adoption ADR"
    pass "step 2.6 model-compare"
    ;;

  --skip)
    reason="${2:-no reason given}"
    echo "SKIP: $reason"
    ;;

  "")
    echo "Usage: $0 <step-id>  (e.g. 1.1–1.7, 2.1–2.6, --skip 'reason')"
    exit 1
    ;;

  *)
    fail "unknown step '$STEP'"
    ;;
esac
