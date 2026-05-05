# TODO — Dam

> **세션 재개 프롬프트**: "TODO.md 확인하고 `## Now`부터 이어서 진행해"

## Now (진행 중, 1~3개)
- [ ] Phase 3 Step 3.1: feature/phase3-designfs1 브랜치 생성 + DESIGNFS1 SMB 마운트

## Next (이번 마일스톤 — Phase 3 준비)
- [ ] Step 3.2 scope-survey: designfs1_mirror realm DB 적재 범위 확정
- [ ] Step 3.3 ingest-designfs1: 1.66M 파일 인제스트

## Later (백로그 — Phase 3+)
- [ ] DESIGNFS1 5TB 확장 PoC — hash_worker.py 전체 실행 (Phase 3 완료 후)
- [ ] inotify 기반 증분 인덱싱 (Phase 5)
- [ ] API 외부 노출 (Caddy + 인증)

## Done (최근 5개만)
- [x] Web UI — /search_text 브라우저 UI (api/static/index.html) (2026-05-05)
- [x] Step 2.3 open-embed-full — open_clip 160,036건 err=0 (471s) (2026-05-05)
- [x] Step 2.4 cn-embed-full — cn_clip 160,036건 err=0 (594s), 총 320k 임베딩 (2026-05-05)
- [x] Step 2.5 text-search-api — /search_text 추가, /similar ?model=, /stats 모델별 분리 (2026-05-05)
- [x] Step 2.6 model-compare — ADR-007: clip-vit-b32 기본, cn_clip 선택 유지 (2026-05-05)
- [x] Step 2.2 worker-impl — clip_worker.py 재작성 + smoke 1000건 PASS (2026-04-28)
