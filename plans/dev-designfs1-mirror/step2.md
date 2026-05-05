# Step 3.2: scope-survey

> GitHub: 미생성 | Milestone: designfs1-mirror

## 읽어야 할 파일
- `docs/PRD.md` (확장자별 규모 표)
- `docs/scan-analysis-1.md`, `scan-analysis-2.md`, `scan-analysis-3.md` (Phase 1 인벤토리 분석)

## 작업
- DESIGNFS1 전수 스캔 (메타만, DB 미적재):
  ```bash
  find /mnt/designfs1 -type f -printf '%s\t%p\n' > /tmp/designfs1_scan.tsv
  ```
- 통계 계산:
  - 전체 파일 수, 총 용량
  - 확장자별 카운트·용량 TOP 20 (특히 PSD/PSB 비중)
  - 탑폴더별 분포
- PRD 의 인벤토리 (Phase 1 시점) 와 drift 비교:
  - 신규/삭제된 파일 카운트 (있다면)
  - PSD 비중이 PRD 의 98.1% 와 일치하는지
- `docs/phase3-survey.md` 작성:
  - 통계 표
  - PSD 제외 시 실제 ingest 대상 수·용량 결정
  - 예상 thumbnail 수 (이미지 확장자 합계)
- 데이터 source 결정: DESIGNFS1 가 (a) DESIGNFS 의 미러인지 (b) 부분 사본인지 (c) 신규 데이터인지 명시

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.2
```
- `docs/phase3-survey.md` 존재
- 통계 표 포함 (확장자·탑폴더)
- PSD 제외 ingest 대상 카운트·용량 명시 (예: "1.66M 파일 / 1.48 TB")
- 데이터 source 성격 명시 (mirror / 부분 / 신규)

## 금지사항
- 이 단계에서 DB INSERT 하지 마라. 이유: 다음 step 책임. 통계만.
- 모든 파일을 읽지 마라 (size + path 메타만). 이유: 1.48 TB 전수 read = 수 시간 낭비.
