# Step 2.6: model-compare

> GitHub: 미생성 | Milestone: clip-embedding

## 읽어야 할 파일
- `api/search.py` (`/search_text`, `/similar/{id}`)
- `docs/PRD.md` (검색 요구사항)

## 작업
- 한국어·영문 query 10–15개 정의 (디자인 에셋 컨텍스트):
  - 한국어: "강아지", "그라데이션 배경", "키즈 캐릭터", "타이포그래피 포스터", "브랜드 로고", "썸네일", "버튼 디자인" 등
  - 영문: "blue gradient", "kid character", "logo", "typography poster", "thumbnail" 등
  - 시각 유사도(이미지-이미지): 임의 자산 5개 골라 `/similar` 두 모델 결과 비교
- 두 모델 각각 `/search_text` 호출 → top-10 결과 캡처
- 비교 항목:
  - 한국어 query 정확도 (subjective top-5 hit rate)
  - 영문 query 정확도
  - 시각 유사도 일치율
  - 응답 latency p50 / p95 (50–100회 반복)
- `docs/clip-comparison.md` 신규 — 표·결과 캡처·정성 평가
- `docs/ADR.md` 에 ADR-00X "CLIP 모델 채택" 추가 — 단일 채택 또는 듀얼 운영(텍스트 검색은 cn_clip, 시각 유사는 open_clip 등) 결정

## Acceptance Criteria
```bash
bash .claude/verify.sh 2.6
```
- `docs/clip-comparison.md` 존재 + 한국어·영문 query 결과 표 포함
- `docs/ADR.md` 에 신규 ADR (`ADR-XXX: CLIP 모델 채택`) 항목 존재
- 채택 결정 명시 (단일 모델 또는 모델별 역할 분리)

## 금지사항
- 자동 메트릭(top-1 acc, mAP) 만으로 결정하지 마라. 이유: 라벨된 ground truth 없음. 정성 검수가 1차.
- ADR 결정 전에 운영용 코드(API 기본값 변경 등)를 만지지 마라. 이유: 결정 → 코드 순서.
