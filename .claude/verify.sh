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
    http_cn=$(curl -o /dev/null -s -w "%{http_code}" --get --data-urlencode "q=강아지" "http://localhost:18000/search_text?model=cn-clip-vitb16&limit=5")
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

  3.5)
    base="http://localhost:18000"

    # Get a real asset_id from poc_sample
    aid=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT asset_id FROM asset_storage WHERE realm='poc_sample' LIMIT 1;" 2>/dev/null | tr -d ' ')
    [[ -n "$aid" ]] || fail "3.5: cannot get test asset_id"

    # 1. Add tag (POST 201)
    resp=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
      -H "Content-Type: application/json" -H "X-User: testuser" \
      -d '{"name":"verify-tag-3.5","namespace":"user"}' \
      "${base}/assets/${aid}/tags")
    [[ "$resp" == "201" ]] || fail "3.5 tag POST → HTTP $resp"

    # Get tag_id
    tag_id=$(curl -fsS "${base}/tags?prefix=verify-tag-3.5" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(d['tags'][0]['id'])" 2>/dev/null)
    [[ -n "$tag_id" ]] || fail "3.5 GET /tags prefix search returned nothing"

    # 2. Search by tag → result includes our asset
    found=$(curl -fsS "${base}/search_text?q=&tag=verify-tag-3.5&limit=5" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(any(r['asset_id']==${aid} for r in d['results']))" 2>/dev/null)
    [[ "$found" == "True" ]] || fail "3.5 tag search did not return tagged asset"

    # 3. Remove tag (DELETE 204)
    code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
      "${base}/assets/${aid}/tags/${tag_id}")
    [[ "$code" == "204" ]] || fail "3.5 tag DELETE → HTTP $code"

    # 4. Orphan cleanup: tag should be gone
    cnt=$(curl -fsS "${base}/tags?prefix=verify-tag-3.5" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['tags']))" 2>/dev/null)
    [[ "${cnt:-1}" -eq 0 ]] || fail "3.5 orphan tag not cleaned up"

    # 5. Collection: create + add assets + verify sort_order
    coll_id=$(curl -fsS -X POST -H "Content-Type: application/json" -H "X-User: testuser" \
      -d '{"name":"verify-coll-3.5"}' "${base}/collections" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null)
    [[ -n "$coll_id" ]] || fail "3.5 collection POST failed"

    # Add 3 assets
    aids=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT array_agg(asset_id) FROM (SELECT asset_id FROM asset_storage WHERE realm='poc_sample' LIMIT 3) t;" 2>/dev/null | tr -d ' {}')
    curl -s -o /dev/null -X POST -H "Content-Type: application/json" \
      -d "{\"asset_ids\":[${aids}]}" "${base}/collections/${coll_id}/assets"

    # Verify sort_order preserved
    orders=$(curl -fsS "${base}/collections/${coll_id}/assets" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print([a['sort_order'] for a in d['assets']])" 2>/dev/null)
    [[ "$orders" != "[]" ]] || fail "3.5 collection assets empty"

    # Cleanup
    curl -s -o /dev/null -X DELETE "${base}/collections/${coll_id}"

    # 6. Concurrent tagging (alice + bob same asset)
    curl -s -o /dev/null -X POST -H "Content-Type: application/json" -H "X-User: alice" \
      -d '{"name":"concurrent-test","namespace":"user"}' "${base}/assets/${aid}/tags"
    curl -s -o /dev/null -X POST -H "Content-Type: application/json" -H "X-User: bob" \
      -d '{"name":"concurrent-test","namespace":"user"}' "${base}/assets/${aid}/tags"
    cnt=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM asset_tags at JOIN tags t ON t.id=at.tag_id WHERE at.asset_id=${aid} AND t.name='concurrent-test';" 2>/dev/null | tr -d ' ')
    [[ "${cnt:-0}" -eq 1 ]] || fail "3.5 concurrent tag conflict: cnt=$cnt (expected 1)"

    # Cleanup concurrent test
    ctag=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT id FROM tags WHERE name='concurrent-test';" 2>/dev/null | tr -d ' ')
    curl -s -o /dev/null -X DELETE "${base}/assets/${aid}/tags/${ctag}" 2>/dev/null

    pass "step 3.5 tags-collections (tag CRUD + orphan + collection sort_order + concurrent OK)"
    ;;

  3.4)
    base="http://localhost:18000"
    check_http() {
      local url="$1" label="$2"
      code=$(curl -o /dev/null -s -w "%{http_code}" "$url")
      [[ "$code" == "200" ]] || fail "3.4 $label → HTTP $code"
      echo "  OK $label"
    }

    # 1. ext filter: results all .jpg
    resp=$(curl -fsS "${base}/search_text?q=poster&ext=jpg&limit=10" 2>/dev/null)
    code=$(curl -o /dev/null -s -w "%{http_code}" "${base}/search_text?q=poster&ext=jpg&limit=10")
    [[ "$code" == "200" ]] || fail "3.4 test1 ext=jpg → HTTP $code"
    bad=$(echo "$resp" | python3 -c "
import json,sys
d=json.load(sys.stdin)
bad=[r for r in d['results'] if r.get('primary_ext') not in ('.jpg','.jpeg',None)]
print(len(bad))" 2>/dev/null)
    [[ "${bad:-0}" -eq 0 ]] || fail "3.4 test1: non-jpg results=$bad"

    # 2. folder filter: 200 (empty OK)
    check_http "${base}/search_text?q=&folder=11.NEXT_UI&limit=5" "test2 folder"

    # 3. role filter: 200
    check_http "${base}/search_text?q=character&role=poster&limit=5" "test3 role"

    # 4. year filter: 200
    check_http "${base}/search_text?q=&year_from=2025&year_to=2025&limit=5" "test4 year"

    # 5. size filter: results all ≥ 10 MB
    resp=$(curl -fsS "${base}/search_text?q=&size_min_mb=10&limit=10" 2>/dev/null)
    code=$(curl -o /dev/null -s -w "%{http_code}" "${base}/search_text?q=&size_min_mb=10&limit=10")
    [[ "$code" == "200" ]] || fail "3.4 test5 size_min_mb → HTTP $code"
    bad=$(echo "$resp" | python3 -c "
import json,sys
d=json.load(sys.stdin)
bad=[r for r in d['results'] if (r.get('size_bytes') or 0) < 10*1024*1024]
print(len(bad))" 2>/dev/null)
    [[ "${bad:-0}" -eq 0 ]] || fail "3.4 test5: results below 10MB count=$bad"

    # /filename_search endpoint exists
    check_http "${base}/filename_search?q=poster&limit=5" "filename_search"

    pass "step 3.4 search-filters (all 5 scenarios + filename_search OK)"
    ;;

  3.3)
    total=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM asset_storage WHERE realm='poc_sample';" 2>/dev/null)
    hashed=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
       WHERE s.realm='poc_sample' AND a.sha256 IS NOT NULL AND a.sha256 <> 'ERROR';" 2>/dev/null)
    hash_pct=$(echo "scale=1; ${hashed:-0} * 100 / ${total:-1}" | bc)
    (( $(echo "$hash_pct >= 95" | bc -l) )) || fail "sha256 fill=${hash_pct}% (need ≥95%)"

    dup_edges=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM asset_edges WHERE relation='duplicate_of';" 2>/dev/null)
    [[ "${dup_edges:-0}" -gt 0 ]] || fail "asset_edges duplicate_of count=0 (need >0)"

    test -f "$REPO/docs/dedup-report.md" || fail "docs/dedup-report.md missing"
    grep -q "절약" "$REPO/docs/dedup-report.md" || fail "dedup-report.md missing 절약 capacity info"

    pass "step 3.3 hash-dedup (sha256=${hash_pct}% dup_edges=${dup_edges})"
    ;;

  3.2)
    # Check GIN indexes exist
    idx_count=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM pg_indexes WHERE tablename='assets' AND indexname IN \
       ('idx_assets_folder_tokens','idx_assets_filename_tokens','idx_assets_year_hint','idx_assets_role_hint');" 2>/dev/null)
    [[ "${idx_count:-0}" -eq 4 ]] || fail "GIN indexes count=$idx_count (need 4)"

    total=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM asset_storage WHERE realm='poc_sample';" 2>/dev/null)
    [[ "${total:-0}" -ge 80000 ]] || fail "poc_sample assets total=$total (need ≥80000)"

    path_done=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
       WHERE s.realm='poc_sample' AND a.folder_tokens IS NOT NULL;" 2>/dev/null)
    path_pct=$(echo "scale=1; ${path_done:-0} * 100 / ${total:-1}" | bc)
    (( $(echo "$path_pct >= 95" | bc -l) )) || fail "folder_tokens fill=${path_pct}% (need ≥95%)"

    img_total=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
       WHERE s.realm='poc_sample' AND a.primary_ext IN ('.jpg','.jpeg','.png','.tiff','.tif','.webp','.bmp','.gif','.heic','.heif','.psd');" 2>/dev/null)
    exif_done=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
       WHERE s.realm='poc_sample' AND a.metadata_json IS NOT NULL;" 2>/dev/null)
    exif_pct=$(echo "scale=1; ${exif_done:-0} * 100 / ${img_total:-1}" | bc)
    (( $(echo "$exif_pct >= 90" | bc -l) )) || fail "metadata_json fill=${exif_pct}% of images (need ≥90%)"

    year_done=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
       WHERE s.realm='poc_sample' AND a.year_hint IS NOT NULL;" 2>/dev/null)
    year_pct=$(echo "scale=1; ${year_done:-0} * 100 / ${total:-1}" | bc)
    (( $(echo "$year_pct >= 30" | bc -l) )) || fail "year_hint fill=${year_pct}% (need ≥30%)"

    role_done=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
       WHERE s.realm='poc_sample' AND array_length(a.role_hint,1) > 0;" 2>/dev/null)
    role_pct=$(echo "scale=1; ${role_done:-0} * 100 / ${total:-1}" | bc)
    (( $(echo "$role_pct >= 20" | bc -l) )) || fail "role_hint fill=${role_pct}% (need ≥20%)"

    pass "step 3.2 metadata-and-tokens (path=${path_pct}% exif=${exif_pct}% year=${year_pct}% role=${role_pct}%)"
    ;;

  3.1)
    branch=$(git -C "$REPO" rev-parse --abbrev-ref HEAD)
    [[ "$branch" == "feature/mvp-features" ]] \
      || fail "branch=$branch (expected feature/mvp-features)"
    test -f "$REPO/plans/_archived/dev-designfs1-mirror/index.json" \
      || fail "plans/_archived/dev-designfs1-mirror/index.json missing"
    step_count=$(ls "$REPO/plans/dev-mvp-features"/step*.md 2>/dev/null | wc -l)
    [[ "${step_count:-0}" -ge 7 ]] \
      || fail "dev-mvp-features step files count=$step_count (need ≥7)"
    pass "step 3.1 archive-and-branch"
    ;;

  3.6)
    # 1. OCR 완료율 ≥ 80% (이미지 자산 기준)
    img_total=$(psql_q "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
      WHERE s.realm='poc_sample' AND a.thumbnail_path IS NOT NULL \
      AND a.primary_ext IN ('.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff')")
    ocr_done=$(psql_q "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
      WHERE s.realm='poc_sample' AND a.thumbnail_path IS NOT NULL \
      AND a.primary_ext IN ('.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff') \
      AND a.ocr_done_at IS NOT NULL")
    ocr_pct=$(echo "scale=1; ${ocr_done:-0} * 100 / ${img_total:-1}" | bc)
    (( $(echo "$ocr_pct >= 80" | bc -l) )) || fail "ocr_done_at fill=${ocr_pct}% (need ≥80%)"

    # 2. 텍스트 추출률 ≥ 25% (처리된 이미지 기준, length > 5)
    ocr_text=$(psql_q "SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id \
      WHERE s.realm='poc_sample' AND a.thumbnail_path IS NOT NULL \
      AND a.primary_ext IN ('.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff') \
      AND a.ocr_done_at IS NOT NULL AND length(a.ocr_text) > 5")
    text_pct=$(echo "scale=1; ${ocr_text:-0} * 100 / ${ocr_done:-1}" | bc)
    (( $(echo "$text_pct >= 25" | bc -l) )) || fail "ocr_text(>5) fill=${text_pct}% of processed (need ≥25%)"

    # 3. 한글 OCR 검색 → 결과 ≥ 1
    code=$(curl -o /dev/null -s -w "%{http_code}" \
      --get --data-urlencode "q=포스터" \
      "http://localhost:18000/search_text?text_search=ocr_only&limit=5")
    [[ "$code" == "200" ]] || fail "3.6 OCR search → HTTP $code"
    cnt=$(curl -fsS --get --data-urlencode "q=포스터" \
      "http://localhost:18000/search_text?text_search=ocr_only&limit=5" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('results',[])))" 2>/dev/null)
    [[ "${cnt:-0}" -ge 1 ]] || fail "3.6 OCR '포스터' search returned 0 results"

    # 4. idx_assets_ocr_tsv GIN 인덱스 존재 확인
    idx=$(psql_q "SELECT indexname FROM pg_indexes WHERE tablename='assets' AND indexname='idx_assets_ocr_tsv'")
    [[ "$idx" == "idx_assets_ocr_tsv" ]] || fail "3.6 idx_assets_ocr_tsv GIN index missing"

    pass "step 3.6 ocr-pipeline (done=${ocr_pct}% text=${text_pct}% search OK idx OK)"
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
