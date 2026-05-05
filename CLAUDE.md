@../CLAUDE.md

## Purpose
Dam — 80 TB 디자인 에셋 AI 관리 시스템. 원본 NAS 불변 원칙 하에 메타데이터·썸네일·CLIP 임베딩·검색 API 를 구축한다.

## Stack
Python 3.12 / FastAPI + uvicorn / PostgreSQL 16 + pgvector / Redis 7 / Docker Compose / WSL2

## Active Work
- Branch: `feature/clip-embedding` → wrap 후 main 머지 예정
- clip-embedding milestone 완료 (2026-05-05): 160,036건 × 2모델 임베딩, /search_text API
- poc_sample: `D:\Work\dam_poc_sample` (161k 파일/58 GB) → DB realm=poc_sample 161,030 + 썸네일 160,036 + 임베딩 320,072
- 다음: feature/clip-embedding → main 머지 후 Phase 3 계획

## Where to look
- 상세 TODO: `@TODO.md`
- 기획: `@docs/PRD.md`
- 아키텍처: `@docs/ARCHITECTURE.md`
- 의사결정: `@docs/ADR.md`
- 이관 현황: `@docs/migration-status.md`
- 스캔 분석: `@docs/scan-analysis-1.md`, `@docs/scan-analysis-2.md`, `@docs/scan-analysis-3.md`
- 초기 기획 검토: `@docs/initial-review.md`
- 진행 중 plan: `@plans/dev-clip-embedding/index.json`
- 이전 task plan: `@plans/dev-server-migration/index.json`
