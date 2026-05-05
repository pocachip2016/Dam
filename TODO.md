# TODO — Dam

> **세션 재개 프롬프트**: "TODO.md 확인하고 `## Now`부터 이어서 진행해"

## Now (진행 중, 1~3개)

## Next (이번 마일스톤 — Phase 3 준비)

## Later (백로그 — Phase 3+)
- [ ] DESIGNFS1 5TB 확장 PoC (PSD 제외, hash_worker.py 실행)
- [ ] inotify 기반 증분 인덱싱 (Phase 5)
- [ ] API 외부 노출 (Caddy + 인증)
- [ ] `/etc/fstab` SMB 영속 등록

## Done (최근 5개만)
- [x] Web UI — /search_text 브라우저 UI (api/static/index.html) (2026-05-05)
- [x] Step 2.3 open-embed-full — open_clip 160,036건 err=0 (471s) (2026-05-05)
- [x] Step 2.4 cn-embed-full — cn_clip 160,036건 err=0 (594s), 총 320k 임베딩 (2026-05-05)
- [x] Step 2.5 text-search-api — /search_text 추가, /similar ?model=, /stats 모델별 분리 (2026-05-05)
- [x] Step 2.6 model-compare — ADR-007: clip-vit-b32 기본, cn_clip 선택 유지 (2026-05-05)
- [x] Step 2.2 worker-impl — clip_worker.py 재작성 + smoke 1000건 PASS (2026-04-28)
