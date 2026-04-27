# Step 2.1: env-prepare-gpu

> GitHub: 미생성 | Milestone: clip-embedding

## 읽어야 할 파일
- `requirements.txt` (현 베이스 의존성)
- `docs/ARCHITECTURE.md` (CLIP·embeddings 위치)
- `nvidia-smi` 출력 (Driver 591.74, CUDA 13.1, RTX 4060 8 GB)

## 작업
- `requirements-gpu.txt` 신규 — torch (cu124 wheel) + open_clip_torch + cn_clip + ftfy/regex (CLIP 토크나이저 의존)
- `.venv` 에 GPU 의존성 설치
- 모델 캐시 위치를 `~/Work/Dam/dam_data/models/` 로 환경변수 export 패턴 정립 (gitignore 됨)
- `nvidia-smi` 와 `torch.cuda.is_available()` 동시 통과 확인
- open_clip 과 cn_clip 의 `from_pretrained` 한 번씩 실행해 모델 다운로드 캐시 확인 (~600 MB + 한국어 모델 별도)

### 설치 패턴 (예)
```bash
.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
.venv/bin/pip install open_clip_torch cn_clip ftfy regex
```

## Acceptance Criteria
```bash
bash .claude/verify.sh 2.1
```
- `torch.cuda.is_available()` == True
- `import open_clip; import cn_clip` 모두 성공
- `~/Work/Dam/dam_data/models/` 존재 (gitignore 됨)

## 금지사항
- CPU-only torch wheel 설치하지 마라. 이유: RTX 4060 GPU 활용이 본 task 의 핵심.
- 모델 캐시를 `/mnt/d/...` 에 두지 마라. 이유: drvfs metadata 부하, 모델 로딩 매번 느림. ext4 native 사용.
- `requirements.txt` 와 GPU 의존성을 섞지 마라. 이유: GPU 없는 환경(CI 등)에서 베이스 의존성만 설치 가능해야 함.
