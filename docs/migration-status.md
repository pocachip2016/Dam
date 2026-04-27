# 🔖 재개 포인트 (Resume Point)

> 최종 업데이트: 2026-04-27
> **서버 이관 Phase 2 재구축 완료** (RTX 4060 PC, feature/server-migration).
> Steps 1.1–1.7 모두 PASS. 다음: Step 1.8 wrap (커밋·GitHub 이슈·이관 보고).

---

## 이관 후 검증 결과 (2026-04-27)

| 항목 | 값 |
|---|---|
| 환경 | RTX 4060 PC / WSL2 / Ubuntu 22.04 |
| poc_sample 위치 | `D:\Work\dam_poc_sample` (= `/mnt/d/Work/dam_poc_sample`) |
| 원본 | `\\designfs.ktalpha.com\DESIGNFS\디자인파트\11.NEXT_UI_2022_10월오픈` |
| 복사 (rsync) | 161,096 파일 / 58.01 GB / PSD·PSB·zip·노이즈 제외 |
| DB 적재 | 161,030 자산 / realm=poc_sample / 7.7분 |
| 썸네일 | 160,036개 / 3.9 GB / 16분 (WORKERS=4) |
| `/stats` | 200 OK — files=161,030, thumbs=160,036, embedded=0 |
| `/search?q=NEXT&realm=poc_sample` | 200 OK — total=21,292 hits |
| `/asset/<id>` | 200 OK — JSON 정상, 한글 경로 UTF-8 |
| `/thumb/<id>` | 200 image/jpeg ✅ |

### API 기동 명령 (새 세션 시)
```bash
cd /home/ktalpha/Work/Dam
docker compose up -d
PYTHONPATH=/home/ktalpha/Work/Dam DAM_DSN=postgresql://dam:dam@localhost:15432/dam \
  .venv/bin/uvicorn api.search:app --host 127.0.0.1 --port 18000
# http://localhost:18000/stats
# http://localhost:18000/docs
```

> ⚠ `__main__` 직접 실행(`python api/search.py`) 시 `PYTHONPATH` 필요 — 모듈 경로 이슈. 향후 코드 수정 backlog.

---

## 다음 시작 시 첫 번째 할 일

### ① Step 1.8 wrap — 커밋·푸시·GitHub 이슈 생성
```bash
# 커밋 후
git push -u origin feature/server-migration
gh issue create ...  # step 1–8 이슈 + milestone
```

### ② CLIP 임베딩 워커 (별도 task)
RTX 4060 활용 — `ingest/clip_worker.py` 작성 후 `/similar/<id>` 검증.

### ③ Phase 3 준비 (DESIGNFS1 5TB PoC)
- DESIGNFS1(`/mnt/designfs1`) 이미 마운트됨
- hash_worker.py 실행 (SHA-256 중복 탐지)
- PSD 제외 전체 적재 검토

### ② CLIP 임베딩 — RTX 4060 기기 이관 후

GTX 750 1GB는 CLIP 불가. RTX 4060 기기 이관 후:
1. `ingest/clip_worker.py` 작성 (open-clip 또는 transformers 사용)
2. `python ingest/clip_worker.py` 실행
3. `/similar/<id>` API 엔드포인트 검증

### ③ Phase 3 준비 (DESIGNFS1 5TB PoC)

- DESIGNFS1 SMB 마운트 경로 확정
- 쓰기 권한 확인
- hash_worker.py 실행 (SHA-256 중복 탐지)

---

## 2026-04-23 오늘 완료한 것

| 항목 | 결과 |
|------|------|
| 환경 사전점검 | Docker v29.4.0 OK / D: 287 GB 여유 / scan_logs 25개 확인 |
| GPU | WSL2에서 GTX 750 (1GB) 인식 — RTX 4060은 다른 기기, 나중에 이관 예정 |
| Docker Compose 기동 | dam_postgres:15432 / dam_redis:16379 정상 |
| DB 볼륨 경로 변경 | `/mnt/d/` NTFS → `/home/pocachip/dam_data/` WSL2 ext4 (NTFS는 chmod 미지원) |
| DDL 자동 적용 | 6테이블 + v_source_files 뷰 + 인덱스 모두 정상 |
| 전량 적재 | **2,080,379개 / 81.22 TB** / 에러 0 / 소요 72분 |
| SHA-256 해시 워커 | `ingest/hash_worker.py` 구현 완료 (실행은 Phase 3 직전) |
| Phase 2 robocopy | D:로 스크립트 복사 완료, 인코딩 문제로 실행 미완 |

---

## Phase 1 Task 목록 (완료)

1. ☑ NEXT.md 업데이트
2. ☑ 환경 사전점검 (Docker/GPU/드라이브)
3. ☑ Docker Compose 구성 (`docker-compose.yml`)
4. ☑ DB 스키마 (`db/migrations/001_init.sql`) + DDL 적용
5. ☑ UTF-16 인벤토리 파서 (`ingest/ingest_inventory.py`)
6. ☑ 전량 적재 — 2,080,379개 / 81.22 TB / 25 scan_runs / 에러 0
7. ☑ SHA-256 해시 워커 (`ingest/hash_worker.py`) — 실행은 Phase 3 직전

## Phase 2 Task 목록

- ☑ `scripts/phase2_robocopy.ps1` 작성 (36개 명령, ~31 GB, PSD 제외)
- ☑ robocopy 완료 — 2026-04-23 17:39 / 81,124개 / 42 GB
- ☑ 001_init.sql 재적용 (Docker 재시작 후 볼륨 초기화)
- ☑ 002_embeddings.sql 적용 (embeddings 테이블 + HNSW 인덱스 + thumbnail_path 컬럼)
- ☑ `ingest/ingest_local.py` 작성 — 로컬 파일 직접 스캔 → DB 적재
- ☑ `ingest/thumbnail_worker.py` 작성
- ☑ `api/search.py` 작성 (FastAPI, 파일명/유사도 검색)
- ☑ poc_sample DB 적재 완료 — 81,117개 / 44.83 GB (2026-04-24 12:03)
- ☑ 썸네일 생성 완료 — 79,853개 / 9개 오류(1억px 초과 초대형 이미지) (2026-04-24 12:45)
- ☑ 검색 API 기동 + 검증 — `api/search.py` 포트 18000 (파일명·확장자·유사도)
- ☐ CLIP 임베딩 워커 (`ingest/clip_worker.py`) — RTX 4060 기기 이관 후

---

## 인프라 현황

| 항목 | 값 |
|------|-----|
| Docker | v29.4.0 (Desktop), WSL2 연동 OK |
| PostgreSQL | dam_postgres:15432 (healthy) |
| Redis | dam_redis:16379 (up) |
| DB 볼륨 | `/home/pocachip/dam_data/pg_data/` (WSL2 ext4) |
| 코드 | `/home/pocachip/work/Dam/` |
| 스캔 로그 | `D:\dam_analysis\scan_logs\inv_*.txt` (25개) |
| Phase 2 샘플 대상 | `D:\dam_analysis\poc_sample\` (~31 GB, 복사 진행 중) |
| GPU (현 PC) | GTX 750 1GB — CLIP 불가, RTX 4060 기기로 이관 후 사용 |

### Docker 재시작 방법 (다음 세션)
```bash
cd /home/pocachip/work/Dam
docker compose up -d
# healthy 확인
docker compose ps
```

---

## DB 적재 결과 (Phase 1 기준)

| 확장자 | 파일 수 | 용량 |
|--------|--------|------|
| .psd | 416,159 | 74 TB |
| .psb | 3,065 | 5.7 TB |
| .jpg | 808,904 | 566 GB |
| .zip | 24,523 | 412 GB |
| .png | 467,410 | 96 GB |
| .ai | 6,024 | 86 GB |
| 합계 | **2,080,379** | **81.22 TB** |

탑레벨 최대: `07. 최근작업물_공유` 127만 파일 / 65 TB

---

## 승인된 5-Phase 계획

| Phase | 목적 | 규모 | 상태 |
|---|---|---|---|
| 1 | 메타데이터 DB + 전량 선적재 | 208만 행 | ✅ 완료 |
| 2 | 로컬 PoC (파이프라인 검증) | ~31 GB 샘플 | ✅ 완료 (CLIP 제외) |
| 3 | DESIGNFS1 확장 PoC (PSD 제외) | ~5 TB | 대기 |
| 4 | PSD 포함 + 서버 이관 | 1~2 TB 추가 | 대기 |
| 5 | AI 분해·재결합 그래프 | — | 대기 |

---

## 아키텍처 결정 (확정)

**Dual Store + Unified Graph** — `architecture_dual_store_graph.md` 참조

- **Source realm**: 원본 NAS 경로 불변, 읽기 전용
- **Derivative realm**: AI 생성·분해물, hash-addressed (`dam_cas`)
- **Graph**: `asset_edges` — duplicate_of / variant_of / derived_from / version_of 등
- **가상 뷰**: `asset_tags` 다축 태그 + `views` 저장 쿼리 → 물리 재구조화 없음

### Phase 2+ 확장 마이그레이션 (미작성)
- `db/migrations/002_embeddings.sql` — vector(512) + HNSW 인덱스
- `db/migrations/003_thumbnails.sql`
- `db/migrations/004_ocr.sql`

---

## 확인 대기 항목

- [ ] Phase 2 robocopy 완료 확인
- [ ] RTX 4060 기기로 코드 이관 시점 결정
- [ ] NAS SMB 마운트 경로 확정 (hash_worker / clip_worker용)
- [ ] DESIGNFS1 쓰기 권한 및 공유 경로 (Phase 3 준비)
- [ ] 포트 충돌 여부 (15432/16379/18000)
