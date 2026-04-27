# TODO — Dam

> **세션 재개 프롬프트**: "TODO.md 확인하고 `## Now`부터 이어서 진행해"

## Now (진행 중, 1~3개)
- [ ] **CLIP 임베딩** `plans/dev-clip-embedding/` — Step 2.1 env-prepare-gpu 진행 예정

## Next (CLIP 임베딩 task)
- [ ] Step 2.1 env-prepare-gpu — torch+cuda + open_clip + cn_clip
- [ ] Step 2.2 worker-impl — `ingest/clip_worker.py` (open/cn 동시 지원)
- [ ] Step 2.3 open-embed-full — open_clip ViT-B/32 전량 임베딩
- [ ] Step 2.4 cn-embed-full — CN-CLIP ViT-B/16 전량 임베딩
- [ ] Step 2.5 text-search-api — `/search_text` 엔드포인트 추가
- [ ] Step 2.6 model-compare — `docs/clip-comparison.md` + ADR 결정
- [ ] Step 2.7 wrap — 커밋·푸시·GitHub 이슈·머지

## Later (백로그 — Phase 3+)
- [ ] DESIGNFS1 5TB 확장 PoC (PSD 제외, hash_worker.py 실행)
- [ ] inotify 기반 증분 인덱싱 (Phase 5)
- [ ] API 외부 노출 (Caddy + 인증)
- [ ] `/etc/fstab` SMB 영속 등록

## Done (최근 5개만)
- [x] Step 1.3 env-prepare — docker-compose 경로 수정 + venv + requirements.txt (2026-04-27)
- [x] Step 1.4 infra-up — dam_postgres healthy + pgvector + HNSW (2026-04-27)
- [x] Step 1.5 nas-mount — DESIGNFS+DESIGNFS1 마운트 + poc_sample 161k파일/58 GB rsync (2026-04-27)
- [x] Step 1.6 data-load — assets/storage 161,030 + thumbnails 160,036 (2026-04-27)
- [x] Step 1.7 api-smoke — /stats·/search·/asset·/thumb 모두 200 + PASS (2026-04-27)
- [x] Step 1.8 wrap — 커밋·푸시·GitHub 이슈·서버이관 완료 (2026-04-27)
- [x] Phase 2 완료 — 81,117 자산 + 79,853 썸네일 + 검색 API 검증 (이전 PC, 2026-04-24)
