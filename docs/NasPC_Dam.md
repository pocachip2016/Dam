# NAS PC ↔ Dam 서버 실데이터 이관 전략 (Phase 5)

**작성일**: 2026-05-28  
**상태**: 검토 대기 (Phase 4.2 완료 후 구현 예정)  
**범위**: 1.48TB 실데이터 + 분류/메타/CLIP 임베딩 동기화

---

## 현황 분석

### 제약 조건

| 제약 | 영향 | 심각도 |
|------|------|--------|
| NAS PC: 로컬 스토리지 부족 | 1.48TB를 통째로 수신 불가 | 🔴 높음 |
| Dam 서버: NAS 직접 접근 불가 | SMB/NFS 마운트 또는 중계 필요 | 🔴 높음 |
| 이관 범위: 메타/분류/CLIP 포함 | 단순 파일 복사로 불충분 | 🟡 중간 |
| 네트워크 대역폭 | 추정 필요 | 🟡 중간 |

### 현재 아키텍처

```
80TB NAS (designfs1)
    ↑ (SMB/NFS)
NAS PC ──────── (제한 공간)
    ↓ (HTTP? rsync?)
Dam 서버 (local:15432, GPU 있음)
    ↓
PostgreSQL: asset_storage (디렉토리 구조)
PostgreSQL: assets (메타/CLIP)
```

---

## 전략: 증분 동기화 + 분산 처리

### 핵심 원칙

1. **NAS PC는 읽기 전용** (스캔권한 활용)
2. **로컬 저장 최소화** (메니페스트 목록만)
3. **Dam 서버가 SSOT** (DB가 최종 상태)
4. **재시작 가능** (idempotent 배치)

---

## 구현 안내 (2가지 옵션)

### **Option A: HTTP 배치 API (권장)**

**흐름:**
```
NAS PC (scan + read)     →    Dam Server
  ↓                              ↓
파일 목록 조회                 /api/ingest/batch
  ↓                              ↓
썸네일 생성 (병렬)           POST multipart
  ↓                              ↓
메타데이터 추출              {asset_id[], metadata}
  ↓                              ↓
HTTP upload                  GPU worker pool
                                 ↓
                            CLIP 임베딩 + DB 저장
```

**API 예시:**

```bash
# NAS PC에서 배치 단위로 전송 (200~500개/배치 권장)
curl -X POST http://dam-server:18000/api/ingest/batch \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "files=@file1.jpg" \
  -F "files=@file2.jpg" \
  -F "metadata={
    'realm': 'production',
    'folder': '디자인파트/11.NEXT_UI_2022_10월오픈',
    'role_hint': ['poster', 'banner'],
    'year_hint': 2022
  }"

# 응답: {batch_id: 42, processing_eta_sec: 120, status: 'queued'}

# 진행도 확인
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://dam-server:18000/api/ingest/batch/42/status
# → {processed: 180, pending: 20, errors: 0}

# 최종 검증 (realm별)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://dam-server:18000/api/stats
# → {by_realm: [{realm: 'production', files: 240000, thumbs: 239500, embedded: {clip-vit-b32: 239500}}]}
```

**장점:**
- ✅ 로컬 저장 0 (네트워크 기반)
- ✅ 재시도 용이 (배치 ID 기반)
- ✅ 병렬 처리 (여러 배치 동시 upload)

**단점:**
- ❌ 네트워크 안정성 필수
- ❌ 각 배치 upload-process 왕복 시간 누적

**예상 시간 (추정):**
```
배치 크기: 300개 파일
- 스캔 + 썸네일 생성 (NAS PC): 5분/배치
- HTTP upload: 2분/배치
- Dam GPU 처리 (CLIP): 8분/배치
- 합계: 15분/배치

1.48TB ≈ 240k 파일 ÷ 300 = 800배치
800배치 × 15분 = 200시간 ≈ 8.3일 (24시간 연속)
또는 일일 2시간씩: 100일
```

---

### **Option B: rsync + 로컬 배치 (대역폭 제한시)**

**흐름:**
```
NAS PC                    Dam Server
  ↓                            ↑
rsync로 선택 데이터     →  /tmp/ingest_staging/
(대역폭 제어)                  ↓
                        batch_processor.py 실행
                        (썸네일 + CLIP)
                                ↓
                        asset_storage 업데이트
```

**구현 예시:**

```bash
# NAS PC에서: 매일 밤 배치 실행
#!/bin/bash
# nas_sync.sh
LAST_SYNC_TIME="/var/cache/dam_last_sync.ts"
THRESHOLD=$(date -d '1 day ago' +%s)

for folder in /mnt/nas/디자인파트/*; do
  find "$folder" -type f -newermt "@$THRESHOLD" | while read file; do
    rsync -av --bwlimit=10000 "$file" \
      admin@dam-server:/tmp/ingest_staging/
  done
done

# Dam 서버에서: cron으로 후처리 (야간 GPU 유휴시)
# 0 2 * * * python -m ingest.batch_processor --realm production --max-files 5000
```

**장점:**
- ✅ 대역폭 제어 가능
- ✅ 로컬 verify 후 upload (안전성)
- ✅ NAS 부하 분산 (스캔 스케줄링)

**단점:**
- ❌ Dam 서버에 임시 저장 필요 (SSD 공간 ≈100GB)
- ❌ rsync → process → cleanup 파이프라인 복잡

---

## Phase 5 세부 계획

### **5.0 Infrastructure Negotiation (1주)**

- [ ] NAS PC ↔ Dam 서버 네트워크 테스트
  - `iperf3` 대역폭 측정
  - HTTP 왕복 지연 (ping, curl 벤치)
- [ ] Option A vs B 최종 선택
- [ ] 스케줄링: 24/7 vs 야간만 vs 분산

### **5.1 Manifest + Metadata Sync (1주)**

- [ ] NAS 디렉토리 구조 스캔
- [ ] asset_storage 테이블에 행 삽입 (realm='production')
  - physical_path, top_folder, sub_folder, is_authoritative=true
- [ ] 무결성 검증: 파일 존재 + 권한 확인

**산출물:**
```sql
INSERT INTO asset_storage (asset_id, realm, physical_path, ...)
SELECT a.id, 'production', $path, ...
FROM assets a
WHERE a.id IN (SELECT asset_id FROM nightly_scan_results);
```

**예상 시간:** 2~3시간 (240k 파일 스캔)

### **5.2 Thumbnail Batch (NAS PC, 2주)**

- [ ] PIL/Pillow로 썸네일 생성 (200×300 기본)
- [ ] PSD/다중 포맷 처리 (Phase 5.5로 미연기 또는 skip)
- [ ] HTTP upload to Dam (Option A) or rsync (Option B)

**병렬화:** 8 worker threads (NAS PC 활용)

**예상 시간:** 40~60시간 (240k × 0.5초 평균)

### **5.3 CLIP Embedding (Dam GPU, 3주)**

- [ ] 배치 API `/api/ingest/batch` 완성
- [ ] 2 모델 × 240k = 480k 벡터
  - clip-vit-b32: 240시간
  - cn-clip-vitb16: 240시간
  - 병렬화 (dual GPU): 240시간

**스케줄링:** 야간 GPU 사용 (주간 API 요청과 겹치지 않게)

### **5.4 Classification + Mapping (2주, 선택사항)**

- [ ] mediaX 콘텐츠 매핑: 기존 M.2~M.6 규칙 확대
- [ ] 또는 Phase 6 (advanced indexing)으로 미연기

### **5.5 Cleanup + Validation**

- [ ] asset 테이블 통계 재계산
- [ ] 검색 인덱스 재구성
- [ ] 50건 샘플 end-to-end 검증

---

## 네트워크 대역폭 추정

**필요 데이터:**
- 원본 파일: 1.48TB
- 썸네일: 240k × 15KB ≈ 3.6TB (중복 제거시 절약)
- 메타데이터: ≈500MB (무시 가능)

**실제 전송량** (Option A):
```
HTTP 배치: 1.48TB (원본) + 3.6TB (썸네일) ≈ 5TB 총 업로드
평균 100Mbps 대역폭 가정
→ 5TB ÷ 100Mbps = 400분 ≈ 6.7시간 (네트워크만)
```

**따라서 Option A 실제 예상:**
```
Day 1-2: 스캔 + 썸네일 생성 (NAS PC)     : 40시간
Day 3-5: HTTP 배치 업로드 (병렬 8개)     : 6시간 (네트워크 효율)
Day 6-30: CLIP 임베딩 (GPU 야간 처리)    : 240시간 (분산)
─────────────────────────────────────────
총 예상: 30일 (병렬화 및 야간 GPU 활용)
```

---

## 체크리스트 (구현시)

### Phase 5.0 (인프라 협의)

- [ ] NAS PC IP/접근성 확인
- [ ] Dam 서버 ↔ NAS PC ping < 100ms
- [ ] HTTP upload 테스트 (1GB 파일)
- [ ] GPU 메모리 (CLIP batch size 검증)
- [ ] 임시 저장소 (Option B시 /tmp 용량)

### Phase 5.1~5.3 (핵심 구현)

- [ ] `/api/ingest/batch` endpoint 작성
- [ ] NAS PC 스캔 스크립트
- [ ] 배치 재시도 로직
- [ ] 진행도 모니터링 대시보드

### Phase 5.4+ (선택사항)

- [ ] Classification 자동화
- [ ] Mapping 정확도 검증
- [ ] PSD 썸네일 처리

---

## 참고: 기존 매핑 활용

Phase 3 MVP 완료 이후 이미 구축된 것:
- ✅ `/api/mapping/*` — asset-to-content 매핑
- ✅ `/api/admin/*` — classification 리뷰 UI
- ✅ asset_classifications — 분류 결과
- ✅ CLIP 모델 (2가지) — 임베딩 인프라

**따라서 Phase 5는** 기존 파이프라인을 "대규모 데이터셋"에 적용하는 것이 핵심.

---

## 다음 단계

1. **지금 (5월 말):** 4.2.4 (ui-login) + 4.3~4.6 완료
2. **6월 초:** Phase 5.0 infrastructure negotiation 시작
   - NAS PC ↔ Dam 네트워크 테스트
   - Option A/B 확정
3. **6월 중:** 5.1 manifest 동기화 시작 (스캔)
4. **6월 말~7월:** 5.2~5.3 배치 이관 (병렬 실행)

