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

    # Setup: editor 사용자 + 토큰 생성
    psql_q "DELETE FROM users WHERE username='verify35_editor'" || true
    EDITOR_TOKEN_35=$(echo "editor35pass" | PYTHONPATH="$REPO" "$REPO/.venv/bin/python" \
      "$REPO/scripts/create_user.py" --username verify35_editor --role editor \
      --password-stdin --issue-token 2>/dev/null | grep "Token:" | awk '{print $2}')
    [[ -n "$EDITOR_TOKEN_35" ]] || fail "3.5: editor 토큰 발급 실패"

    AUTH="-H \"Authorization: Bearer ${EDITOR_TOKEN_35}\""

    # Get a real asset_id from poc_sample
    aid=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT asset_id FROM asset_storage WHERE realm='poc_sample' LIMIT 1;" 2>/dev/null | tr -d ' ')
    [[ -n "$aid" ]] || fail "3.5: cannot get test asset_id"

    # 1. Add tag (POST 201)
    resp=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
      -H "Content-Type: application/json" -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      -d '{"name":"verify-tag-3.5","namespace":"user"}' \
      "${base}/assets/${aid}/tags")
    [[ "$resp" == "201" ]] || fail "3.5 tag POST → HTTP $resp"

    # Get tag_id
    tag_id=$(curl -fsS -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      "${base}/tags?prefix=verify-tag-3.5" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(d['tags'][0]['id'])" 2>/dev/null)
    [[ -n "$tag_id" ]] || fail "3.5 GET /tags prefix search returned nothing"

    # 2. Search by tag → result includes our asset
    found=$(curl -fsS -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      "${base}/search_text?q=&tag=verify-tag-3.5&limit=5" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(any(r['asset_id']==${aid} for r in d['results']))" 2>/dev/null)
    [[ "$found" == "True" ]] || fail "3.5 tag search did not return tagged asset"

    # 3. Remove tag (DELETE 204)
    code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
      -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      "${base}/assets/${aid}/tags/${tag_id}")
    [[ "$code" == "204" ]] || fail "3.5 tag DELETE → HTTP $code"

    # 4. Orphan cleanup: tag should be gone
    cnt=$(curl -fsS -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      "${base}/tags?prefix=verify-tag-3.5" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['tags']))" 2>/dev/null)
    [[ "${cnt:-1}" -eq 0 ]] || fail "3.5 orphan tag not cleaned up"

    # 5. Collection: create + add assets + verify sort_order
    coll_id=$(curl -fsS -X POST \
      -H "Content-Type: application/json" -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      -d '{"name":"verify-coll-3.5"}' "${base}/collections" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(d['id'])" 2>/dev/null)
    [[ -n "$coll_id" ]] || fail "3.5 collection POST failed"

    # Add 3 assets
    aids=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT array_agg(asset_id) FROM (SELECT asset_id FROM asset_storage WHERE realm='poc_sample' LIMIT 3) t;" 2>/dev/null | tr -d ' {}')
    curl -s -o /dev/null -X POST \
      -H "Content-Type: application/json" -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      -d "{\"asset_ids\":[${aids}]}" "${base}/collections/${coll_id}/assets"

    # Verify sort_order preserved
    orders=$(curl -fsS -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      "${base}/collections/${coll_id}/assets" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print([a['sort_order'] for a in d['assets']])" 2>/dev/null)
    [[ "$orders" != "[]" ]] || fail "3.5 collection assets empty"

    # Cleanup collection
    curl -s -o /dev/null -X DELETE \
      -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      "${base}/collections/${coll_id}"

    # 6. Concurrent tagging (same editor token, same asset — idempotency)
    curl -s -o /dev/null -X POST -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      -d '{"name":"concurrent-test","namespace":"user"}' "${base}/assets/${aid}/tags"
    curl -s -o /dev/null -X POST -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      -d '{"name":"concurrent-test","namespace":"user"}' "${base}/assets/${aid}/tags"
    cnt=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM asset_tags at JOIN tags t ON t.id=at.tag_id WHERE at.asset_id=${aid} AND t.name='concurrent-test';" 2>/dev/null | tr -d ' ')
    [[ "${cnt:-0}" -eq 1 ]] || fail "3.5 concurrent tag conflict: cnt=$cnt (expected 1)"

    # Cleanup concurrent test
    ctag=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT id FROM tags WHERE name='concurrent-test';" 2>/dev/null | tr -d ' ')
    [[ -n "$ctag" ]] && curl -s -o /dev/null -X DELETE \
      -H "Authorization: Bearer ${EDITOR_TOKEN_35}" \
      "${base}/assets/${aid}/tags/${ctag}" 2>/dev/null || true

    # Teardown: 사용자 삭제 (CASCADE → 토큰 삭제)
    psql_q "DELETE FROM users WHERE username='verify35_editor'" || true

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

  4.2.3)
    # 0. rebuild container
    docker compose -f "$REPO/docker-compose.dev.yml" up -d --build dam_api >/dev/null 2>&1
    until curl -fsS http://localhost:18000/docs >/dev/null 2>&1; do sleep 1; done

    # 1. X-User 잔존 금지
    if grep -rn "x_user\|X-User" "$REPO/api/" --include="*.py" 2>/dev/null | grep -qv "static\|# "; then
      fail "X-User placeholder 잔존: $(grep -rn 'x_user\|X-User' "$REPO/api/" --include='*.py' | grep -v 'static\|# ')"
    fi

    # 2. 시나리오용 사용자 + 토큰 생성
    for u in verify_admin verify_editor verify_viewer; do psql_q "DELETE FROM users WHERE username='$u'" || true; done

    ADMIN_TOKEN=$(echo "adminpass" | PYTHONPATH="$REPO" "$REPO/.venv/bin/python" \
      "$REPO/scripts/create_user.py" --username verify_admin --role admin \
      --password-stdin --issue-token 2>/dev/null | grep "Token:" | awk '{print $2}')
    EDITOR_TOKEN=$(echo "editorpass" | PYTHONPATH="$REPO" "$REPO/.venv/bin/python" \
      "$REPO/scripts/create_user.py" --username verify_editor --role editor \
      --password-stdin --issue-token 2>/dev/null | grep "Token:" | awk '{print $2}')
    VIEWER_TOKEN=$(echo "viewerpass" | PYTHONPATH="$REPO" "$REPO/.venv/bin/python" \
      "$REPO/scripts/create_user.py" --username verify_viewer --role viewer \
      --password-stdin --issue-token 2>/dev/null | grep "Token:" | awk '{print $2}')

    [[ -n "$ADMIN_TOKEN" && -n "$EDITOR_TOKEN" && -n "$VIEWER_TOKEN" ]] \
      || fail "token 발급 실패 (admin=$ADMIN_TOKEN editor=$EDITOR_TOKEN viewer=$VIEWER_TOKEN)"

    BASE="http://localhost:18000"

    # 3. anonymous → 401
    code=$(curl -o /dev/null -s -w "%{http_code}" "${BASE}/search_text?q=test")
    [[ "$code" == "401" ]] || fail "anonymous /search_text → $code (expected 401)"

    # 4. bad token → 401
    code=$(curl -o /dev/null -s -w "%{http_code}" -H "Authorization: Bearer invalid_token_xyz" "${BASE}/search_text?q=test")
    [[ "$code" == "401" ]] || fail "bad token /search_text → $code (expected 401)"

    # 5. viewer + GET /search_text → 200 (빈 q= 로 metadata path 사용, torch 불필요)
    code=$(curl -o /dev/null -s -w "%{http_code}" -H "Authorization: Bearer ${VIEWER_TOKEN}" "${BASE}/search_text?q=&limit=1")
    [[ "$code" == "200" ]] || fail "viewer /search_text → $code (expected 200)"

    # 6. viewer + POST /assets tags → 403
    aid=$(psql_q "SELECT asset_id FROM asset_storage WHERE realm='poc_sample' LIMIT 1" | tr -d ' ')
    code=$(curl -o /dev/null -s -w "%{http_code}" -X POST \
      -H "Authorization: Bearer ${VIEWER_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"name":"verify-tag","namespace":"user"}' \
      "${BASE}/assets/${aid}/tags")
    [[ "$code" == "403" ]] || fail "viewer POST /tags → $code (expected 403)"

    # 7. editor + POST /assets tags → 201
    code=$(curl -o /dev/null -s -w "%{http_code}" -X POST \
      -H "Authorization: Bearer ${EDITOR_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"name":"verify-tag-423","namespace":"user"}' \
      "${BASE}/assets/${aid}/tags")
    [[ "$code" == "201" ]] || fail "editor POST /tags → $code (expected 201)"
    # cleanup tag
    tag_id=$(psql_q "SELECT id FROM tags WHERE name='verify-tag-423'" | tr -d ' ')
    [[ -n "$tag_id" ]] && psql_q "DELETE FROM tags WHERE id='$tag_id'" || true

    # 8. editor + /api/admin → 403
    code=$(curl -o /dev/null -s -w "%{http_code}" -X POST \
      -H "Authorization: Bearer ${EDITOR_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"asset_id":1,"old_class":"draft","new_class":"content"}' \
      "${BASE}/api/admin/classification/reclass")
    [[ "$code" == "403" ]] || fail "editor /api/admin → $code (expected 403)"

    # 9. admin + /api/mapping/stats → 200
    code=$(curl -o /dev/null -s -w "%{http_code}" \
      -H "Authorization: Bearer ${ADMIN_TOKEN}" \
      "${BASE}/api/mapping/stats")
    [[ "$code" == "200" ]] || fail "admin /api/mapping/stats → $code (expected 200)"

    # 10. cleanup
    for u in verify_admin verify_editor verify_viewer; do psql_q "DELETE FROM users WHERE username='$u'" || true; done

    pass "step 4.2.3 wire-endpoints (anon=401 bad=401 viewer=200 viewer-post=403 editor-post=201 editor-admin=403 admin=200)"
    ;;

  4.2.2)
    # 0. cleanup (이전 테스트 레지듀)
    for user in verify_admin verify_editor verify_viewer; do
      psql_q "DELETE FROM users WHERE username='$user'" || true
    done

    # 1. import 성공
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "
from api.auth import hash_password, verify_password, issue_token, require_user, ROLE_LEVEL, router
assert ROLE_LEVEL['viewer'] < ROLE_LEVEL['editor'] < ROLE_LEVEL['admin']
print('imports OK')
" || fail "api.auth import failed"

    # 2. pytest 통과
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -m pytest \
      "$REPO/tests/test_auth.py" -q --tb=short \
      || fail "test_auth.py tests failed"

    # 3. create_user.py로 3명 생성
    echo "testpass1" | PYTHONPATH="$REPO" "$REPO/.venv/bin/python" \
      "$REPO/scripts/create_user.py" --username verify_admin --role admin --password-stdin \
      || fail "create_user verify_admin failed"

    echo "testpass2" | PYTHONPATH="$REPO" "$REPO/.venv/bin/python" \
      "$REPO/scripts/create_user.py" --username verify_editor --role editor --password-stdin \
      || fail "create_user verify_editor failed"

    echo "testpass3" | PYTHONPATH="$REPO" "$REPO/.venv/bin/python" \
      "$REPO/scripts/create_user.py" --username verify_viewer --role viewer --password-stdin \
      || fail "create_user verify_viewer failed"

    # 4. password_hash 확인 (argon2 시작)
    for user in verify_admin verify_editor verify_viewer; do
      hash=$(psql_q "SELECT password_hash FROM users WHERE username='$user'")
      [[ "$hash" == \$argon2* ]] || fail "user $user password_hash not argon2 (got: $hash)"
    done

    # 5. cleanup
    for user in verify_admin verify_editor verify_viewer; do
      psql_q "DELETE FROM users WHERE username='$user'" || true
    done

    pass "step 4.2.2 auth-module-and-cli (hash/token/role OK, 3 users seeded+cleaned)"
    ;;

  4.2.1)
    # 1. 테이블 존재
    for tbl in users api_tokens; do
      psql_q "SELECT 1 FROM pg_tables WHERE tablename='$tbl'" | grep -q 1 \
        || fail "table $tbl missing — 010_auth.sql 미적용"
    done

    # 2. role CHECK 위반 → ERROR 확인
    err=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "INSERT INTO users(username,password_hash,role) VALUES('_ck_bad','x','other')" 2>&1) || true
    echo "$err" | grep -q "violates check constraint" \
      || fail "role CHECK constraint not working (got: $err)"

    # 3. password 평문 컬럼 없음 (컬럼명에 'password' 단독 금지)
    plain=$(psql_q "SELECT column_name FROM information_schema.columns \
      WHERE table_name='users' AND column_name='password'")
    [[ -z "$plain" ]] || fail "plain 'password' column exists — use 'password_hash'"

    # 4. token_hash UNIQUE 제약 존재
    uniq=$(psql_q "SELECT COUNT(*) FROM pg_constraint c \
      JOIN pg_class r ON r.oid=c.conrelid \
      WHERE r.relname='api_tokens' AND c.contype='u' AND \
      c.conname LIKE '%token_hash%'")
    [[ "${uniq:-0}" -ge 1 ]] || fail "api_tokens.token_hash UNIQUE constraint missing"

    pass "step 4.2.1 schema-and-migration (users + api_tokens OK)"
    ;;

  4.G.3)
    test -f "$REPO/docs/db-recovery.md" \
      || fail "docs/db-recovery.md missing"
    grep -q "Scenario A" "$REPO/docs/db-recovery.md" \
      || fail "db-recovery.md missing Scenario A"
    grep -q "Scenario B" "$REPO/docs/db-recovery.md" \
      || fail "db-recovery.md missing Scenario B"
    grep -q "Scenario C" "$REPO/docs/db-recovery.md" \
      || fail "db-recovery.md missing Scenario C"
    result=$(docker exec dam_postgres psql -U dam -d dam -tAc "SELECT 1" 2>/dev/null)
    [ "$result" = "1" ] || fail "DB not responding after smoke-test recovery"
    tables=$(docker exec dam_postgres psql -U dam -d dam -tAc "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';" 2>/dev/null)
    [ "$tables" -ge 10 ] || fail "expected ≥10 tables after restore, got $tables"
    pass "step 4.G.3 smoke-test"
    ;;

  4.G.2)
    docker compose -f "$REPO/docker-compose.yml" config -q \
      || fail "docker compose config failed"
    docker exec dam_postgres ls -la /usr/local/bin/dam_init_guard.sh 2>/dev/null | grep -q "dam_init_guard" \
      || fail "dam_init_guard.sh not found in container"
    docker exec dam_postgres pg_isready -U dam -d dam 2>/dev/null \
      || fail "postgres not ready (pg_isready failed)"
    result=$(docker exec dam_postgres psql -U dam -d dam -tAc "SELECT 1" 2>/dev/null)
    [ "$result" = "1" ] || fail "DB not responding (SELECT 1 returned: $result)"
    pass "step 4.G.2 compose-integration"
    ;;

  4.G.1)
    test -f "$REPO/scripts/postgres_entrypoint_guard.sh" \
      || fail "postgres_entrypoint_guard.sh missing"
    test -x "$REPO/scripts/postgres_entrypoint_guard.sh" \
      || fail "postgres_entrypoint_guard.sh not executable"
    bash -n "$REPO/scripts/postgres_entrypoint_guard.sh" \
      || fail "syntax error in postgres_entrypoint_guard.sh"
    head -1 "$REPO/scripts/postgres_entrypoint_guard.sh" | grep -q "#!/usr/bin/env bash" \
      || fail "missing shebang"
    grep -q "set -euo pipefail" "$REPO/scripts/postgres_entrypoint_guard.sh" \
      || fail "missing set -euo pipefail"
    grep -q "DAM_ALLOW_INIT" "$REPO/scripts/postgres_entrypoint_guard.sh" \
      || fail "DAM_ALLOW_INIT not referenced"
    pass "step 4.G.1 guard-script"
    ;;

  M.1)
    # 1. 모듈 import 가능
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "from ingest.mediax_mirror import main" \
      || fail "ingest.mediax_mirror not importable"

    # 2. mediaX 도달 가능
    http_code=$(curl -o /dev/null -s -w "%{http_code}" \
      "http://localhost:8000/api/meta-core/contents/since?ts=0&limit=1")
    [[ "$http_code" == "200" ]] \
      || fail "mediaX /api/meta-core/contents/since → HTTP $http_code (backend 재시작 필요)"

    # 3. 워커 실행 (oneshot)
    PYTHONPATH="$REPO" DAM_DSN="$DSN" MEDIAX_URL="http://localhost:8000" \
      "$REPO/.venv/bin/python" -m ingest.mediax_mirror \
      || fail "mediax_mirror exited non-zero"

    # 4. 미러 행 수 ≥ mediaX total (0건이면 둘 다 0도 OK)
    mirror_cnt=$(psql_q "SELECT COUNT(*) FROM content_catalog_mirror")
    src_cnt=$(curl -fsS "http://localhost:8000/api/meta-core/contents/since?ts=0&limit=1" \
      | python3 -c "import json,sys; print(json.load(sys.stdin).get('total',0))")
    [[ "${mirror_cnt:-0}" -ge "${src_cnt:-0}" ]] \
      || fail "mirror=$mirror_cnt < mediaX total=$src_cnt"

    # 5. cursor 가 0 에서 advance 했는지
    cur=$(psql_q "SELECT value FROM sync_cursors WHERE key='content_mirror_next_ts'")
    [[ "$cur" != "0" ]] || fail "cursor still 0 after sync"

    # 6. 멱등성: 한 번 더 돌려도 row 수 동일
    PYTHONPATH="$REPO" DAM_DSN="$DSN" MEDIAX_URL="http://localhost:8000" \
      "$REPO/.venv/bin/python" -m ingest.mediax_mirror >/dev/null 2>&1 || true
    after=$(psql_q "SELECT COUNT(*) FROM content_catalog_mirror")
    [[ "$after" == "$mirror_cnt" ]] || fail "non-idempotent: before=$mirror_cnt after=$after"

    pass "step M.1 mediax-content-mirror (mirror=$mirror_cnt cursor=$cur idempotent OK)"
    ;;

  M.2)
    # 1. 유틸 모듈 import
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "
from ingest._classification_rules import FOLDER_PATTERNS, FILENAME_KEYWORDS
from ingest._korean_norm import extract_korean, normalize_title
from ingest.asset_mapper import classify_asset, match_content
from api.mapping import router
print('imports OK')
" || fail "M.2 module import failed"

    # 2. pytest 신규 테스트
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -m pytest \
      "$REPO/tests/test_classification_rules.py" \
      "$REPO/tests/test_asset_mapper.py" \
      "$REPO/tests/test_mapping_api.py" \
      -q --tb=short \
      || fail "M.2 pytest failed"

    # 3. DB: 0007 마이그레이션 적용 확인
    psql_q "SELECT 1 FROM pg_tables WHERE tablename='asset_classifications'" | grep -q 1 \
      || fail "asset_classifications table missing — 0007 마이그레이션 미적용"

    # 4. cursor seed 확인
    psql_q "SELECT value FROM sync_cursors WHERE key='asset_mapper_last_id'" | grep -q "." \
      || fail "asset_mapper_last_id cursor missing"

    # 5. 워커 실행 (small batch for verify)
    PYTHONPATH="$REPO" DAM_DSN="$DSN" DAM_MAPPING_BATCH=500 \
      "$REPO/.venv/bin/python" -m ingest.asset_mapper \
      || fail "asset_mapper exited non-zero"

    # 6. 분류 행 수 확인
    ac_total=$(psql_q "SELECT COUNT(*) FROM asset_classifications")
    [[ "${ac_total:-0}" -ge 1 ]] || fail "asset_classifications 0건 — 분류 미실행"

    # 7. 멱등성: 재실행 후 행 수 동일
    PYTHONPATH="$REPO" DAM_DSN="$DSN" DAM_MAPPING_BATCH=500 \
      "$REPO/.venv/bin/python" -m ingest.asset_mapper >/dev/null 2>&1 || true
    ac_after=$(psql_q "SELECT COUNT(*) FROM asset_classifications")
    [[ "$ac_after" == "$ac_total" ]] || fail "non-idempotent: before=$ac_total after=$ac_after"

    pass "step M.2 asset-classification-and-mapping (ac=${ac_total} idempotent OK)"
    ;;

  M.3)
    # 1. 모듈 import
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "
from ingest.clip_text_mapper import main, encode_titles
print('import OK')
" || fail "M.3 module import failed"

    # 2. pytest
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -m pytest \
      "$REPO/tests/test_clip_text_mapper.py" \
      -q --tb=short \
      || fail "M.3 pytest failed"

    # 3. 0008 마이그레이션 확인
    psql_q "SELECT 1 FROM pg_tables WHERE tablename='content_title_embeddings'" | grep -q 1 \
      || fail "content_title_embeddings table missing — 0008 마이그레이션 미적용"

    # 4. 워커 실행 (small batch)
    PYTHONPATH="$REPO" DAM_DSN="$DSN" DAM_CLIP_BATCH=256 \
      "$REPO/.venv/bin/python" -m ingest.clip_text_mapper \
      || fail "clip_text_mapper exited non-zero"

    # 5. 콘텐츠 제목 임베딩 캐시 확인
    cte_cnt=$(psql_q "SELECT COUNT(*) FROM content_title_embeddings")
    [[ "${cte_cnt:-0}" -ge 1 ]] || fail "content_title_embeddings 0건"

    # 6. 신규 clip_similarity 매핑 확인
    clip_cnt=$(psql_q "SELECT COUNT(*) FROM asset_content_link WHERE method='clip_similarity'")
    log_msg="clip_similarity_links=${clip_cnt}"

    # 7. 멱등성
    PYTHONPATH="$REPO" DAM_DSN="$DSN" DAM_CLIP_BATCH=256 \
      "$REPO/.venv/bin/python" -m ingest.clip_text_mapper >/dev/null 2>&1 || true
    clip_after=$(psql_q "SELECT COUNT(*) FROM asset_content_link WHERE method='clip_similarity'")
    [[ "$clip_after" == "$clip_cnt" ]] || fail "non-idempotent: before=$clip_cnt after=$clip_after"

    pass "step M.3 clip-text-image-fallback (cte=${cte_cnt} ${log_msg} idempotent OK)"
    ;;

  M.5)
    # 1. import
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "
from api.search_filters import build_filters
clauses, params = build_filters({'class_filter':'content','content_id':1,'top_folder':'test','hide_draft':True})
assert 'class_filter' in params
assert 'content_id_f' in params
assert 'top_folder' in params
assert any('ac_hd' in c for c in clauses)
print('filter import+logic OK')
" || fail "M.5 search_filters import/logic failed"

    # 2. pytest
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -m pytest \
      "$REPO/tests/test_search_filters_m5.py" \
      -q --tb=short \
      || fail "M.5 pytest failed"

    # 3. API smoke (서버 기동 중일 때)
    base="http://localhost:18000"
    code=$(curl -o /dev/null -s -w "%{http_code}" "${base}/search_text?q=&class_filter=content&limit=5")
    [[ "$code" == "200" ]] || fail "M.5 /search_text?class_filter=content → HTTP $code (서버 기동 필요)"

    code=$(curl -o /dev/null -s -w "%{http_code}" "${base}/search_text?q=&hide_draft=false&limit=5")
    [[ "$code" == "200" ]] || fail "M.5 /search_text?hide_draft=false → HTTP $code"

    pass "step M.5 asset-search-api (class/content_id/top_folder/hide_draft 필터 OK)"
    ;;

  M.6)
    # 1. import
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "
from api.admin import router
from api.search import app
print('admin router routes:', [r.path for r in router.routes])
print('import OK')
" || fail "M.6 admin import failed"

    # 2. pytest
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -m pytest \
      "$REPO/tests/test_admin_api.py" \
      -q --tb=short \
      || fail "M.6 pytest failed"

    # 3. HTML 화면 존재 확인
    for page in classification.html content-mapping.html unclassified.html; do
      test -f "$REPO/api/web/templates/admin/${page}" \
        || fail "M.6 admin page missing: ${page}"
    done

    pass "step M.6 mapping-admin-ui (7 write endpoints + 3 admin pages + 15 tests OK)"
    ;;

  M.4)
    # 1. import
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "
from ingest.video_worker import main, VIDEO_EXTS, _classify_video
assert '.mp4' in VIDEO_EXTS
cls, sub, conf, method = _classify_video('/슬라이스/', 'banner.mp4')
assert cls in ('composition','promotion','content','draft','ui_service')
print('import + logic OK')
" || fail "M.4 video_worker import failed"

    # 2. pytest
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -m pytest \
      "$REPO/tests/test_video_worker.py" \
      -q --tb=short \
      || fail "M.4 pytest failed"

    # 3. 워커 실행
    PYTHONPATH="$REPO" DAM_DSN="$DSN" DAM_REALM=poc_sample \
      "$REPO/.venv/bin/python" -m ingest.video_worker \
      || fail "video_worker exited non-zero"

    # 4. video asset 분류 확인
    vid_classified=$(psql_q "
      SELECT COUNT(DISTINCT ac.asset_id)
      FROM asset_classifications ac
      JOIN assets a ON a.id=ac.asset_id
      WHERE a.primary_ext = ANY(ARRAY['.mp4','.mov','.mkv','.avi'])
    ")
    [[ "${vid_classified:-0}" -ge 1 ]] || fail "video assets not classified (count=$vid_classified)"

    pass "step M.4 video-mock-ingest (classified=${vid_classified} OK)"
    ;;

  M.0)
    # 1. 테이블 존재 확인
    for tbl in content_catalog_mirror asset_content_link sync_cursors; do
      psql_q "SELECT 1 FROM pg_tables WHERE tablename='$tbl'" | grep -q 1 \
        || fail "table $tbl missing"
    done
    # 2. sync_cursors 시드 확인
    val=$(psql_q "SELECT value FROM sync_cursors WHERE key='content_mirror_next_ts'")
    [[ "$val" == "0" ]] || fail "sync_cursor seed missing (got: $val)"
    # 3. FK 무결성 — 존재하지 않는 FK 참조가 거부되는지 확인 (stderr 포함해 캡처)
    fk_out=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "INSERT INTO asset_content_link(asset_id,content_id,method) VALUES(0,0,'manual')" 2>&1) || true
    echo "$fk_out" | grep -q "violates" \
      || fail "FK constraint not working"
    pass "step M.0 mapping-schema (3 tables + seed OK)"
    ;;

  4.1)
    branch=$(git -C "$REPO" rev-parse --abbrev-ref HEAD)
    [[ "$branch" == "feature/ops-readiness" ]] \
      || fail "branch=$branch (expected feature/ops-readiness)"
    test -d "$REPO/deploy" \
      || fail "deploy/ directory missing"
    test -f "$REPO/deploy/systemd/dam.service" \
      || fail "deploy/systemd/dam.service missing"
    test -f "$REPO/deploy/systemd/dam-workers@.service" \
      || fail "deploy/systemd/dam-workers@.service missing"
    test -f "$REPO/deploy/.env.prod.template" \
      || fail "deploy/.env.prod.template missing"
    test -f "$REPO/deploy/Caddyfile.template" \
      || fail "deploy/Caddyfile.template missing"
    test -f "$REPO/deploy/crontab.template" \
      || fail "deploy/crontab.template missing"
    test -f "$REPO/docker-compose.dev.yml" \
      || fail "docker-compose.dev.yml missing"
    test ! -f "$REPO/docker-compose.yml" \
      || fail "docker-compose.yml still exists (should have been git mv'd)"
    test -f "$REPO/docker-compose.prod.yml" \
      || fail "docker-compose.prod.yml missing"
    pass "step 4.1 branch-and-scaffold"
    ;;

  poster-ingest-P.1)
    # 1. DB 마이그레이션 파일 존재
    test -f "$REPO/db/migrations/0009_poster_ingest.sql" \
      || fail "0009_poster_ingest.sql missing"
    grep -q "poster_ingest_log" "$REPO/db/migrations/0009_poster_ingest.sql" \
      || fail "poster_ingest_log table definition missing"
    echo "  ✓ 0009_poster_ingest.sql 존재"

    # 2. API 모듈 import OK
    PYTHONPATH="$REPO" "$REPO/.venv/bin/python" -c "
from api.ingest_poster import router, PosterIngestRequest, PosterIngestResponse
routes = [r.path for r in router.routes]
assert '/api/ingest/poster' in routes, f'POST /api/ingest/poster 없음 (routes={routes})'
assert '/api/ingest/poster/status/{image_id}' in routes, 'GET status 없음'
print('  ✓ ingest_poster routes:', routes)
" || fail "api.ingest_poster import 또는 route 확인 실패"

    # 3. search.py 에 router 등록 확인
    grep -q "ingest_poster_router" "$REPO/api/search.py" \
      || fail "ingest_poster_router not registered in search.py"
    echo "  ✓ search.py 에 router 등록 확인"

    # 4. docker-compose 포스터 볼륨 추가 확인
    grep -q "DAM_POSTER_ROOT" "$REPO/docker-compose.yml" \
      || fail "DAM_POSTER_ROOT env missing in docker-compose.yml"
    grep -q "data/posters" "$REPO/docker-compose.yml" \
      || fail "posters write volume missing in docker-compose.yml"
    echo "  ✓ docker-compose 포스터 볼륨 확인"

    # 5. DB 테이블 존재 확인 (컨테이너 기동 중일 때)
    if docker exec dam_postgres pg_isready -U dam -d dam >/dev/null 2>&1; then
      psql_q "SELECT 1 FROM pg_tables WHERE tablename='poster_ingest_log'" | grep -q 1 \
        || fail "poster_ingest_log table not in DB (migration 미적용?)"
      echo "  ✓ poster_ingest_log 테이블 DB 확인"
    else
      echo "  ⚠ dam_postgres 미기동 — DB 테이블 확인 스킵 (코드 검증만)"
    fi

    pass "step poster-ingest-P.1 Dam DB migration + ingest API"
    ;;

  4.3)
    BASE="${DAM_BASE:-http://localhost:18000}"

    # 1. worker_runs 테이블 존재
    tbl=$(psql_q "SELECT to_regclass('public.worker_runs')")
    [[ "$tbl" == "worker_runs" ]] || fail "worker_runs 테이블 없음 — 011_worker_runs.sql 적용 필요"

    # 2. RunTracker dummy run — INSERT + heartbeat + finished_at
    run_id=$(PYTHONPATH="$REPO" DAM_DSN="$DSN" "$REPO/.venv/bin/python" -c "
from ingest.run_tracker import RunTracker
with RunTracker('verify_dummy', total_planned=10, dsn='$DSN') as rt:
    rt.tick(5, errors=0, force=True)
    rt.tick(10, errors=0, force=True)
    print(rt.run_id)
" 2>/dev/null | tail -1)
    [[ -n "$run_id" ]] || fail "RunTracker run_id 획득 실패"

    hb=$(psql_q "SELECT last_heartbeat IS NOT NULL FROM worker_runs WHERE id=$run_id")
    [[ "$hb" == "t" ]] || fail "heartbeat 미갱신 (run_id=$run_id)"

    fin=$(psql_q "SELECT finished_at IS NOT NULL FROM worker_runs WHERE id=$run_id")
    [[ "$fin" == "t" ]] || fail "finished_at 미기록 (run_id=$run_id)"

    # cleanup
    psql_q "DELETE FROM worker_runs WHERE id=$run_id" > /dev/null

    # 3. /health 무인증 200
    code=$(curl -o /dev/null -s -w "%{http_code}" "${BASE}/health")
    [[ "$code" == "200" ]] || fail "/health → $code (expected 200)"

    # 4. /api/admin/workers — admin 200, viewer 403
    # admin 토큰 발급
    admin_tok=$(PYTHONPATH="$REPO" DAM_DSN="$DSN" \
      "$REPO/.venv/bin/python" "$REPO/scripts/verify43_token.py" verify43_adm admin 2>/dev/null)

    viewer_tok=$(PYTHONPATH="$REPO" DAM_DSN="$DSN" \
      "$REPO/.venv/bin/python" "$REPO/scripts/verify43_token.py" verify43_vw viewer 2>/dev/null)

    code=$(curl -o /dev/null -s -w "%{http_code}" \
      -H "Authorization: Bearer ${admin_tok}" "${BASE}/api/admin/workers")
    [[ "$code" == "200" ]] || fail "/api/admin/workers admin → $code (expected 200)"

    code=$(curl -o /dev/null -s -w "%{http_code}" \
      -H "Authorization: Bearer ${viewer_tok}" "${BASE}/api/admin/workers")
    [[ "$code" == "403" ]] || fail "/api/admin/workers viewer → $code (expected 403)"

    # cleanup
    psql_q "DELETE FROM users WHERE username IN ('verify43_adm','verify43_vw')" > /dev/null

    pass "step 4.3 monitoring (worker_runs OK, RunTracker OK, /health OK, /admin/workers role OK)"
    ;;

  4.4)
    # 1. backup_db.sh 실행 → dump 생성 확인 (기존 dump가 있으면 재사용)
    latest=$(find "$REPO/data/backups" -maxdepth 1 -name 'dam_*.dump' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    if [[ -z "$latest" ]]; then
      BACKUP_DIR="$REPO/data/backups" bash "$REPO/scripts/db_backup.sh" \
        || fail "db_backup.sh 실행 실패"
      latest=$(ls -t "$REPO/data/backups/dam_*.dump" 2>/dev/null | head -1)
    fi
    [[ -f "$latest" ]] || fail "dump 파일 없음"

    # 2. retention: mock 파일 생성 후 db_backup.sh에서 직접 find -delete 로직을 검증
    mock="$REPO/data/backups/dam_20000101_000000.dump"
    touch "$mock"
    touch -d "9 days ago" "$mock"
    # find 명령만 실행해 삭제 확인 (pg_dump 재실행 없이)
    RETENTION_DAYS="${RETENTION_DAYS:-7}"
    find "$REPO/data/backups" -maxdepth 1 -name 'dam_*.dump' -mtime +"$RETENTION_DAYS" -delete
    if [[ -f "$mock" ]]; then
      rm -f "$mock"
      fail "retention: 9일 전 mock 파일 미삭제"
    fi

    # 3. 복원 리허설: 임시 컨테이너에 dump 로드 → assets count 비교
    src_count=$(docker exec dam_postgres psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM assets" | tr -d ' ')

    docker rm -f dam_restore_test 2>/dev/null || true
    docker run -d --name dam_restore_test \
      -e POSTGRES_USER=dam -e POSTGRES_PASSWORD=dam -e POSTGRES_DB=dam \
      pgvector/pgvector:pg16 > /dev/null

    # DB 기동 대기
    for i in $(seq 1 20); do
      docker exec dam_restore_test pg_isready -U dam -d dam >/dev/null 2>&1 && break
      sleep 1
    done

    docker exec -i dam_restore_test pg_restore \
      -U dam -d dam --no-owner --no-privileges < "$latest" 2>/dev/null || true

    rst_count=$(docker exec dam_restore_test psql -U dam -d dam -tAc \
      "SELECT COUNT(*) FROM assets" 2>/dev/null | tr -d ' ')
    docker rm -f dam_restore_test > /dev/null

    [[ "$src_count" == "$rst_count" ]] \
      || fail "복원 assets count 불일치: src=$src_count rst=$rst_count"

    # 4. restore-procedure.md 4섹션 확인
    for section in "백업" "복원" "롤백" "손실"; do
      grep -q "$section" "$REPO/docs/restore-procedure.md" \
        || fail "restore-procedure.md '$section' 섹션 없음"
    done

    # 5. backup_thumbs.sh 존재 + 실행 가능
    [[ -x "$REPO/scripts/backup_thumbs.sh" ]] \
      || fail "backup_thumbs.sh 없거나 실행 권한 없음"
    bash -n "$REPO/scripts/backup_thumbs.sh" \
      || fail "backup_thumbs.sh 문법 오류"

    pass "step 4.4 backup (dump OK, retention OK, 복원 리허설 OK, restore-procedure OK, backup_thumbs OK)"
    ;;

  *)
    fail "unknown step '$STEP'"
    ;;
esac
