@../CLAUDE.md

## Purpose
Dam — 80 TB 디자인 에셋 AI 관리 시스템. 원본 NAS 불변 원칙 하에 메타데이터·썸네일·CLIP 임베딩·검색 API 를 구축한다.

## Stack
Python 3.12 / FastAPI + uvicorn / PostgreSQL 16 + pgvector / Redis 7 / Docker Compose / WSL2

## Active Work
- Phase 3 (mvp-features) ✅ 완료 (2026-05-08): metadata·dedup·search-filters·tags·OCR 전 완료, main 머지
- Phase 4 진행 중: db-init-guard ✅ (entrypoint guard + 주간 백업 cron), 다음: auth·monitoring·ops-readiness
- poc_sample: `D:\Work\dam_poc_sample` (161k 파일/58 GB) → DB realm=poc_sample 161,030 + 썸네일 160,036 + 임베딩 320,072
- Phase 5 첫 배치 ✅ 완료 (2026-07-02): designfs1_mirror(NAS 스캔 2026-06-30, `D:\dam_data\realm`에 로컬 사본) — SRC_REMAP으로 metadata 167,660 + 썸네일 166,703 + 임베딩(open/cn) 각 166,702. 썸네일 base를 `D:\dam_data\thumbnails`로 통합(poc_sample 포함). 19건 카운트 차이 규명 완료(대부분 Office 임시파일, 신규 이미지 5건은 후속 검토). `feature/designfs1-mirror-pipeline`, `plans/dev-designfs1-mirror-pipeline/`

## Where to look
- 상세 TODO: `@TODO.md`
- 기획: `@docs/PRD.md`
- 아키텍처: `@docs/ARCHITECTURE.md`
- 의사결정: `@docs/ADR.md`
- 이관 현황: `@docs/migration-status.md`
- 스캔 분석: `@docs/scan-analysis-1.md`, `@docs/scan-analysis-2.md`, `@docs/scan-analysis-3.md`
- 초기 기획 검토: `@docs/initial-review.md`
- 완료 plan: `@plans/dev-mvp-features/index.json`
- 이전 task plan: `@plans/dev-server-migration/index.json`
