# Step 2.7: wrap

> GitHub: 미생성 | Milestone: clip-embedding

## 읽어야 할 파일
- `TODO.md`, `CLAUDE.md`
- `plans/dev-clip-embedding/index.json`
- `docs/clip-comparison.md`, `docs/ADR.md`

## 작업
- `TODO.md` — Done 갱신, Now 비우기
- `CLAUDE.md` Active Work — Branch: main, 최근: clip-embedding 완료
- `index.json` 모든 step `"completed"` + summary 한 줄
- 커밋 분할 (예: env / worker / embeddings / api / compare / wrap)
- `git push -u origin feature/clip-embedding`
- GitHub milestone "clip-embedding" 생성 + 이슈 7개 생성/close + step{N}.md back-write
- 사용자 승인 후 `--no-ff` 머지 → main → push → 로컬 브랜치 삭제

## Acceptance Criteria
```bash
bash .claude/verify.sh --skip "wrap-up: docs + merge + push"
```

## 금지사항
- 사용자 명시 승인 없이 push / 브랜치 삭제하지 마라. 이유: 워크스페이스 규칙.
- 모델 캐시(`dam_data/models/`) 를 git 에 추가하지 마라. 이유: 600 MB+ 바이너리, gitignore 됨.
