# Step 6: data-load

> GitHub: #7 | Milestone: server-migration

## 결과 요약 (2026-04-27 완료)

| 항목 | 값 |
|---|---:|
| 적재 자산 (`asset_storage` realm=poc_sample) | **161,030** |
| `assets` 행 (1:1 매핑) | 161,030 |
| 누적 용량 | 58.01 GB |
| 썸네일 생성 (`assets.thumbnail_path`) | **160,036** |
| 썸네일 NULL | 994 (959 비이미지 + 35 PIL 에러) |
| ingest 소요 | 459초 (≈7.7분) |
| thumbnail 소요 | 966초 (≈16분, WORKERS=4) |
| verify.sh 1.6 | PASS |

### 폴더별 분포 (TOP 5)
| top_folder | files | GB |
|---|---:|---:|
| @디자인산출물_가로포스터+단편상세 | 95,514 | 26.91 |
| @디자인산출물_오픈VOD | 34,429 | 11.15 |
| ■론칭이후_2022_10월 | 27,467 | 14.61 |
| @모든G | 1,223 | 1.55 |
| 00_가이드 | 508 | 1.97 |

## 읽어야 할 파일
- `ingest/ingest_local.py` (POC_ROOT, DAM_DSN 환경변수, realm 상수)
- `ingest/thumbnail_worker.py` (THUMB_DIR, DAM_DSN, WORKERS 환경변수)
- `plans/dev-server-migration/index.json`
- `plans/dev-server-migration/step5.md` (poc_sample 위치)

## 작업 (수행 명령)

### ① 파일 스캔 + DB 적재
```bash
POC_ROOT=/mnt/d/Work/dam_poc_sample \
DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
.venv/bin/python ingest/ingest_local.py
```
- `realm='poc_sample'` 고정
- `os.walk` + `parse_path` → `(top_folder, sub_folder, filename, ext)` 분해
- COPY FROM STDIN → `_stage` 임시 테이블 → 멱등 중복 제거 → assets/asset_storage/asset_tags 적재
- `SKIP_PREFIXES = ('._', '~$', '_')` 매칭 파일 66건 자동 제외 (rsync 161,096 → ingest 161,030)

### ② 썸네일 생성
```bash
THUMB_DIR=/home/ktalpha/Work/Dam/dam_data/thumbnails \
WORKERS=4 \
DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
.venv/bin/python ingest/thumbnail_worker.py
```
- 대상 확장자: `.jpg .jpeg .png .gif .webp .bmp .tiff .tif`
- 출력: 512px max LANCZOS, JPG 저장, `assets.thumbnail_path` 업데이트
- `ProcessPoolExecutor(max_workers=WORKERS)` 병렬

### ③ 검증
```bash
bash .claude/verify.sh 1.6
```

## Acceptance Criteria
- `SELECT COUNT(*) FROM asset_storage WHERE realm='poc_sample'` ≥ 80,000 → **161,030** ✅
- `SELECT COUNT(*) FROM assets a JOIN asset_storage s ON s.asset_id=a.id WHERE s.realm='poc_sample' AND a.thumbnail_path IS NOT NULL` ≥ 79,000 → **160,036** ✅

## 메모
- 이전 PC (phase 2) 81,117 자산 / 79,853 썸네일 → 새 PC 161,030 / 160,036 (약 2배, 11.NEXT_UI 폴더 전체 통째 복사 영향)
- 35건 PIL 에러는 디버그 레벨로만 기록되어 로그에 없음. 향후 클리닝 task 에서 재시도·CSV 출력 필요 시 코드 수정.
- THUMB_DIR 디폴트가 `/home/pocachip/dam_data/thumbnails` (이전 PC 사용자명) — 환경변수로 덮어씌움. 코드 자체 수정은 별도 task.

## 금지사항
- realm 을 변경하지 마라. 이유: `ingest_local.py` 는 `poc_sample` 고정이며, inventory 재적재는 이번 범위 밖.
- `/mnt/d/Work/dam_poc_sample` 비어있을 때 실행하지 마라. 이유: 빈 적재 후 완료 처리될 수 있음 — Step 5 의 rsync 결과 확인 후 진행.
