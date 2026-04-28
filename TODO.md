# TODO — Dam

> **세션 재개 프롬프트**: "TODO.md 확인하고 `## Now`부터 이어서 진행해"

## Now (진행 중, 1~3개)

## Next (이번 마일스톤 — Phase 2 재구축)
- [ ] Step 2.3 open-embed-full — LIMIT=0로 전체 160k 임베딩 생성
- [ ] Step 1.8 wrap — 커밋·푸시·GitHub 이슈·마이그레이션 보고
- [ ] `api/search.py` PYTHONPATH 이슈 수정 — `__main__` 직접 실행 지원

## Later (백로그 — Phase 3+)
- [ ] DESIGNFS1 5TB 확장 PoC (PSD 제외, hash_worker.py 실행)
- [ ] inotify 기반 증분 인덱싱 (Phase 5)
- [ ] API 외부 노출 (Caddy + 인증)
- [ ] `/etc/fstab` SMB 영속 등록

## Done (최근 5개만)
- [x] Step 2.2 worker-impl — clip_worker.py 재작성 + smoke 1000건 PASS (2026-04-28)
- [x] Step 1.3 env-prepare — docker-compose 경로 수정 + venv + requirements.txt (2026-04-27)
- [x] Step 1.4 infra-up — dam_postgres healthy + pgvector + HNSW (2026-04-27)
- [x] Step 1.5 nas-mount — DESIGNFS+DESIGNFS1 마운트 + poc_sample 161k파일/58 GB rsync (2026-04-27)
- [x] Step 1.6 data-load — assets/storage 161,030 + thumbnails 160,036 (2026-04-27)
- [x] Step 1.7 api-smoke — /stats·/search·/asset·/thumb 모두 200 + PASS (2026-04-27)
- [x] Step 1.8 wrap — 커밋·푸시·GitHub 이슈·서버이관 완료 (2026-04-27)
- [x] Phase 2 완료 — 81,117 자산 + 79,853 썸네일 + 검색 API 검증 (이전 PC, 2026-04-24)
