# TODO — Dam

> **세션 재개 프롬프트**: "TODO.md 확인하고 `## Now`부터 이어서 진행해"

## Now (진행 중, 1~3개)

## Next (이번 마일스톤 — Phase 3 MVP 기능)
- [x] **3.1** archive-and-branch — `feature/mvp-features` 생성 (2026-05-06)
- [x] **3.2** metadata-and-tokens — EXIF/IPTC/XMP + folder/filename tokens + year/role hint (2026-05-06)
- [x] **3.3** hash-dedup — sha256 + duplicate edges + dedup-report (2026-05-06)
- [x] **3.4** search-filters — `/search_text` ext/folder/role/year/size/mtime 필터 (2026-05-06)
- [x] **3.5** tags-collections — 다중 사용자 태그·컬렉션 (2026-05-06)
- [x] **3.6** ocr-pipeline — EasyOCR GPU, ocr_tsv 검색 통합 (2026-05-06)
- [ ] **3.7** wrap

## Later (백로그 — Phase 4+)
- [ ] Phase 4 운영 준비 (auth / monitoring / backup / deployment) — `plans/dev-ops-readiness/`
- [x] dev-asset-content-mapping M.0 — 006_content_mapping.sql 신설 (2026-05-09)
- [x] dev-asset-content-mapping M.1 — 528건 UPSERT, cursor 증분 동기화 (2026-05-09)
- [x] dev-asset-content-mapping M.2~M.6 — 분류·매핑·CLIP fallback·검색필터·어드민 UI 완료 (2026-05-10)
- [ ] Phase 5 실데이터 이관 (단방향 push, ~1.48 TB) — 인프라 협의 후 plan 작성
- [ ] PSD 썸네일 처리 (Phase 5 실데이터 시점)
- [ ] inotify 증분 인덱싱 (Phase 5 후)

## Done (최근 5개만)
- [x] Step 4.G db-init-guard — entrypoint guard + smoke-test A/B/C + db-recovery.md (2026-05-08)
- [x] Step 3.7 wrap — Phase 3 docs 갱신, feature/mvp-features → main 머지 (2026-05-08)
- [x] Step 3.6 ocr-pipeline — EasyOCR GPU, ocr_tsv GIN, 160k 배치, /search_text ocr_only (2026-05-06)
- [x] Step 3.5 tags-collections — 태그 CRUD + orphan 정리 + collection sort_order (2026-05-06)
- [x] Step 3.4 search-filters — ext/folder/role/year/size/mtime/tag 필터 (2026-05-06)
- [x] Step 3.3 hash-dedup — sha256 100%, 8,652 dup edges, 4.0 GB 절약 (2026-05-06)
- [x] Step 3.2 metadata-and-tokens — path/exif/year/role fill 완료 (2026-05-06)
- [x] Web UI — /search_text 브라우저 UI (api/static/index.html) (2026-05-05)
- [x] Step 2.3 open-embed-full — open_clip 160,036건 err=0 (471s) (2026-05-05)
- [x] Step 2.4 cn-embed-full — cn_clip 160,036건 err=0 (594s), 총 320k 임베딩 (2026-05-05)
- [x] Step 2.5 text-search-api — /search_text 추가, /similar ?model=, /stats 모델별 분리 (2026-05-05)
- [x] Step 2.6 model-compare — ADR-007: clip-vit-b32 기본, cn_clip 선택 유지 (2026-05-05)
- [x] Step 2.2 worker-impl — clip_worker.py 재작성 + smoke 1000건 PASS (2026-04-28)
