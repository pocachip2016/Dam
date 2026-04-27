# Step 2: harness-align

> GitHub: #3 | Milestone: server-migration

## 읽어야 할 파일
- `/home/ktalpha/Work/CLAUDE.md` (docs/plans/gitignore 컨벤션)
- `plans/dev-server-migration/index.json`
- `NEXT.md`, `Q1.md`, `scan_anal*.md`, `phase2_sample_plan.md` (이동 전 읽기)
- `docs/{PRD,ARCHITECTURE,ADR}.md` (현재 스켈레톤 확인)

## 작업
- `.gitignore` 신규 — `__pycache__/`, `*.pyc`, `.venv/`, `dam_data/`, `*.smbcredentials`
- `git rm -r --cached api/__pycache__ ingest/__pycache__` (이미 추적된 pyc 제거)
- 루트 .md 이동:
  - `Q1.md` → `docs/initial-review.md`
  - `phase2_sample_plan.md` → `plans/dev-phase2-sample/notes.md`
  - `scan_anal1/2/3.md` → `docs/scan-analysis-1/2/3.md`
  - `NEXT.md` → `docs/migration-status.md`
- `docs/PRD.md` — 프로젝트 목적, 5-Phase 계획, 데이터 규모 (81 TB / 208만 행) 기재
- `docs/ARCHITECTURE.md` — Dual Store + Unified Graph 아키텍처, 디렉토리 구조 기재
- `docs/ADR.md` — ADR-001: Dual Store 결정, ADR-002: pgvector + HNSW 선택 기재
- `TODO.md` — NEXT.md/NEXT.md 의 Phase 상태를 Now/Next/Later/Done 으로 변환
- `CLAUDE.md` Active Work — Branch/최근/plan 갱신

## Acceptance Criteria
```bash
bash .claude/verify.sh 1.2
```

## 금지사항
- 정보를 삭제하지 마라. 이유: 이전 PC 의 결정·결과물은 모두 보존해야 함.
- `dam_data/` 를 git 에 추가하지 마라. 이유: 로컬 DB 볼륨, gitignore 대상.
