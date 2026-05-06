# Step 3.1: archive-and-branch

> GitHub: 미생성 | Milestone: mvp-features

## 읽어야 할 파일
- `CLAUDE.md` (Branch convention)
- `plans/dev-mvp-features/index.json`
- `plans/_archived/dev-designfs1-mirror/` (참고: 폐기된 SMB-기반 plan)

## 작업
- main 에서 분기:
  ```bash
  git checkout main
  git pull
  git checkout -b feature/mvp-features
  ```
- 향후 step 의존성 파악만 — `requirements.txt` 일괄 추가 X (각 step 에서 필요 시 추가):
  - 3.2: `pyexiftool` 또는 `exifread` + `python-xmp-toolkit`
  - 3.3: 기존 `hash_worker.py` 재활용
  - 3.6: `paddleocr` (GPU) + `langdetect`, fallback `pytesseract`
- TODO.md `## Now` 항목을 Step 3.2 metadata-and-tokens 로 교체

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.1
```
- `git rev-parse --abbrev-ref HEAD` == `feature/mvp-features`
- `plans/_archived/dev-designfs1-mirror/index.json` 존재 (archive 보존)
- `plans/dev-mvp-features/` 7 step file 존재

## 금지사항
- main 에서 직접 작업 금지. 이유: branch convention.
- archived plan 파일 삭제 금지. 이유: 의사결정 추적 근거.
- requirements.txt 일괄 추가 금지. 이유: 각 step 의존성 격리 + 좁은 롤백.
