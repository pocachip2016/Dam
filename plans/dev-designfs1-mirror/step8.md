# Step 3.8: wrap

> GitHub: 미생성 | Milestone: designfs1-mirror

## 읽어야 할 파일
- `TODO.md`, `CLAUDE.md`
- `plans/dev-designfs1-mirror/index.json`
- `docs/phase3-survey.md`, `docs/phase3-dedup-report.md`, `docs/phase3-perf.md`

## 작업
- `docs/PRD.md` Phase 3 줄: `대기` → `✅ 완료` 갱신
- `TODO.md` — Done 갱신, Now 비우기, Later 백로그 정리
- `CLAUDE.md` Active Work — Phase 3 완료 명시, 다음 Phase 4 (PSD 포함 + 운영) 예정 표시
- `index.json` 모든 step `"completed"` + summary 한 줄
- 커밋 분할 (예: ingest / thumb / embed / hash / perf-docs / wrap)
- `git push -u origin feature/phase3-designfs1`
- 사용자 승인 후 `--no-ff` 머지 → main → push → 로컬 브랜치 삭제

## Acceptance Criteria
```bash
bash .claude/verify.sh --skip "wrap-up: docs + merge + push 완료"
```
- `docs/PRD.md` Phase 3 행 `✅ 완료`
- `git log --oneline main` 에 머지 커밋 존재
- 로컬 브랜치 `feature/phase3-designfs1` 삭제됨

## 금지사항
- 사용자 명시 승인 없이 push / 브랜치 삭제하지 마라. 이유: 워크스페이스 규칙.
- 썸네일/임베딩 디렉토리(`dam_data/thumbnails_designfs1/`, `dam_data/models/`) 를 git 에 추가하지 마라. 이유: 수십 GB 바이너리, gitignore 됨.
- DESIGNFS1 SMB 자격증명을 커밋에 노출하지 마라. 이유: 보안.
