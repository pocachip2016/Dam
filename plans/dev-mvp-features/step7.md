# Step 3.7: wrap

> GitHub: 미생성 | Milestone: mvp-features

## 읽어야 할 파일
- `TODO.md`, `CLAUDE.md`, `docs/PRD.md`
- `plans/dev-mvp-features/index.json`
- `docs/dedup-report.md`

## 작업
- `docs/PRD.md` Phase 3 줄: `대기` → `✅ 완료` 갱신
- `TODO.md` — Done 갱신, Now 비우기, Phase 4 항목 Next 로 승격
- `CLAUDE.md` Active Work — Phase 3 (mvp-features) 완료 명시, Phase 4 (운영 준비) 예정 표시
- `plans/dev-mvp-features/index.json` 모든 step `"completed"` + summary 한 줄
- 커밋 분할 (예: archive / metadata-tokens / hash-dedup / search-filters / tags-collections / ocr / docs)
- `git push -u origin feature/mvp-features`
- 사용자 승인 후 `--no-ff` 머지 → main → push → 로컬 브랜치 삭제

## Acceptance Criteria
```bash
bash .claude/verify.sh --skip "wrap-up: docs + merge + push 완료"
```
- `docs/PRD.md` Phase 3 행 `✅ 완료`
- `git log --oneline main` 에 `feature/mvp-features` 머지 커밋 존재
- 로컬 브랜치 `feature/mvp-features` 삭제됨

## 금지사항
- 사용자 명시 승인 없이 push / 머지 / 브랜치 삭제 금지. 이유: workspace 규칙.
- 썸네일/임베딩/모델 디렉토리 git 추가 금지. 이유: 수십 GB, gitignored.
