@../CLAUDE.md

## Purpose
Dam — 80 TB 디자인 에셋 AI 관리 시스템. 원본 NAS 불변 원칙 하에 메타데이터·썸네일·CLIP 임베딩·검색 API 를 구축한다.

## Stack
Python 3.12 / FastAPI + uvicorn / PostgreSQL 16 + pgvector / Redis 7 / Docker Compose / WSL2

## Active Work
- Branch: `feature/server-migration`
- Phase 2 완료 (이전 PC). 새 PC (RTX 4060) 로 이관 진행 중.
- 서버이관 완료 (2026-04-27): feature/server-migration → main 머지 예정
- poc_sample: `D:\Work\dam_poc_sample` (161k 파일/58 GB) → DB realm=poc_sample 161,030 + 썸네일 160,036

## Where to look
- 상세 TODO: `@TODO.md`
- 기획: `@docs/PRD.md`
- 아키텍처: `@docs/ARCHITECTURE.md`
- 의사결정: `@docs/ADR.md`
- 이관 현황: `@docs/migration-status.md`
- 스캔 분석: `@docs/scan-analysis-1.md`, `@docs/scan-analysis-2.md`, `@docs/scan-analysis-3.md`
- 초기 기획 검토: `@docs/initial-review.md`
- 진행 중 plan: `@plans/dev-server-migration/index.json`
