# TODO — Dam

> **세션 재개 프롬프트**: "TODO.md 확인하고 `## Now`부터 이어서 진행해"

## Now (진행 중, 1~3개)
- [ ] **4.2.4** ui-login — login.html + app.js + index.html 전환
- [ ] **B.2.0** TMDB 이미지 다중 ingest 엔드포인트 (mediaX Plan B 후속) —
      feature/tmdb-image-ingest, plans/dev-tmdb-image-ingest/. B.2.0.0(스키마) 완료,
      B.2.0.1(엔드포인트)/B.2.0.2(테스트) 남음

## Next (이번 마일스톤 — Phase 4 ops-readiness)
- [x] **3.1** archive-and-branch — `feature/mvp-features` 생성 (2026-05-06)
- [x] **3.2** metadata-and-tokens — EXIF/IPTC/XMP + folder/filename tokens + year/role hint (2026-05-06)
- [x] **3.3** hash-dedup — sha256 + duplicate edges + dedup-report (2026-05-06)
- [x] **3.4** search-filters — `/search_text` ext/folder/role/year/size/mtime 필터 (2026-05-06)
- [x] **3.5** tags-collections — 다중 사용자 태그·컬렉션 (2026-05-06)
- [x] **3.6** ocr-pipeline — EasyOCR GPU, ocr_tsv 검색 통합 (2026-05-06)
- [ ] **3.7** wrap

## Later (백로그 — Phase 4+)
- [ ] Phase 4 운영 준비 (auth / monitoring / backup / deployment) — `plans/dev-ops-readiness/`
  - [x] 4.1 branch-and-scaffold (2026-05-28) — feature/ops-readiness + deploy/ scaffold
  - [x] 4.2.1 schema-and-migration (2026-05-28) — users + api_tokens table
  - [x] 4.2.2 auth-module-and-cli (2026-05-28) — argon2, token, require_user, create_user.py
  - [x] 4.2.3 wire-endpoints (2026-05-28) — all endpoints viewer/editor/admin gates, X-User removed
  - [ ] 4.2.4 ui-login — login.html form + app.js helper + index.html redirect
  - [ ] 4.3 monitoring — worker_runs table, /admin/workers API + dashboard
  - [ ] 4.4 backup — backup_db.sh/backup_thumbs.sh, restore-procedure.md
  - [ ] 4.5 deployment — docker-compose.prod.yml complete, systemd units, deployment.md
  - [ ] 4.6 wrap — PRD/TODO/CLAUDE.md update, operations.md, main merge
- [x] dev-asset-content-mapping M.0 — 006_content_mapping.sql 신설 (2026-05-09)
- [x] dev-asset-content-mapping M.1 — 528건 UPSERT, cursor 증분 동기화 (2026-05-09)
- [x] dev-asset-content-mapping M.2~M.6 — 분류·매핑·CLIP fallback·검색필터·어드민 UI 완료 (2026-05-10)
- [x] Phase 5 첫 배치 — designfs1_mirror(167,665건) metadata/thumbnail/clip/OCR 전체 완료 (2026-07-03) — `plans/dev-designfs1-mirror-pipeline/`
- [ ] Phase 5 나머지 실데이터 이관 (단방향 push, ~1.48 TB) — 인프라 협의 후 plan 작성
- [ ] PSD 썸네일 처리 (Phase 5 실데이터 시점)
- [ ] inotify 증분 인덱싱 (Phase 5 후)

## Done (최근 5개만)
- [x] Phase 5 첫 배치 wrap — designfs1_mirror metadata/thumbnail/clip/OCR 전체 완료(166,704건, errors=0) + 신규 이미지 5건 ingest (2026-07-03)
- [x] Phase 5 첫 배치 — 썸네일 base `D:\dam_data\thumbnails` 통합 (2026-07-02)
- [x] Step 4.G db-init-guard — entrypoint guard + smoke-test A/B/C + db-recovery.md (2026-05-08)
- [x] Step 3.7 wrap — Phase 3 docs 갱신, feature/mvp-features → main 머지 (2026-05-08)
- [x] Step 3.6 ocr-pipeline — EasyOCR GPU, ocr_tsv GIN, 160k 배치, /search_text ocr_only (2026-05-06)
