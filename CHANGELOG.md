# CHANGELOG — Dam

> `TODO.md`의 `## Done`은 최근 5개만 유지. 초과분은 여기로 이관.

- [x] Step 3.4 search-filters — ext/folder/role/year/size/mtime/tag 필터 (2026-05-06)
- [x] Step 3.3 hash-dedup — sha256 100%, 8,652 dup edges, 4.0 GB 절약 (2026-05-06)
- [x] Step 3.2 metadata-and-tokens — path/exif/year/role fill 완료 (2026-05-06)
- [x] Web UI — /search_text 브라우저 UI (api/static/index.html) (2026-05-05)
- [x] Step 2.3 open-embed-full — open_clip 160,036건 err=0 (471s) (2026-05-05)
- [x] Step 2.4 cn-embed-full — cn_clip 160,036건 err=0 (594s), 총 320k 임베딩 (2026-05-05)
- [x] Step 2.5 text-search-api — /search_text 추가, /similar ?model=, /stats 모델별 분리 (2026-05-05)
- [x] Step 2.6 model-compare — ADR-007: clip-vit-b32 기본, cn_clip 선택 유지 (2026-05-05)
- [x] Step 2.2 worker-impl — clip_worker.py 재작성 + smoke 1000건 PASS (2026-04-28)
