# Dam 백업 & 복원 절차

> 장애 발생 시 빠른 복구를 위한 운영 절차서.
> DB 장애 대응 상세 → [`docs/db-recovery.md`](db-recovery.md)

---

## 1. 백업 일정

| 대상 | 스크립트 | 주기 | 보존 | 저장 위치 |
|------|----------|------|------|-----------|
| **DB dump** | `scripts/db_backup.sh` | 매일 03:00 | 7일 | `data/backups/dam_*.dump` |
| **썸네일** | `scripts/backup_thumbs.sh` | 매주 일요일 04:00 | 전체 | `data/thumb_backup/` |
| **모델** | `scripts/backup_thumbs.sh` | 최초 1회 (--ignore-existing) | 전체 | `data/model_backup/` |

**크론 설치:**
```bash
crontab deploy/crontab.template   # dam 사용자로 실행
```

**수동 실행:**
```bash
bash scripts/db_backup.sh         # DB 즉시 백업
bash scripts/backup_thumbs.sh     # 썸네일 즉시 백업
```

**임베딩 백업 없음** — DB `embeddings` 테이블에 저장, 모델+썸네일에서 재생성 가능.

---

## 2. 복원 절차

### DB 복원

```bash
# 1. 사용 가능한 dump 목록 확인
ls -lh data/backups/dam_*.dump

# 2. 복원할 dump 지정 (보통 최신)
DUMP=$(ls -t data/backups/dam_*.dump | head -1)

# 3. 컨테이너 상태 확인
docker compose -f docker-compose.dev.yml up -d dam_postgres

# 4. 복원 (기존 스키마·데이터 교체)
docker exec -i dam_postgres pg_restore \
  -U dam -d dam --clean --if-exists --no-owner < "$DUMP"

# 5. 검증
docker exec dam_postgres psql -U dam -d dam \
  -c "SELECT COUNT(*) FROM assets;"
# 예상: 161030
```

> pg_data 자체가 손상된 경우 → [`docs/db-recovery.md` Scenario C](db-recovery.md#scenario-c--의도적-fresh-init--백업-복원) 참고

### 썸네일 복원

```bash
# 백업 → 원본 방향 (--delete 없이 덮어쓰기)
rsync -a data/thumb_backup/ dam_data/thumbnails/
```

---

## 3. 롤백 시나리오

| 상황 | 조치 |
|------|------|
| 복원 중 `pg_restore` 오류 | `data/backups/` 에서 이전 dump 선택 후 재시도 |
| 최신 dump 손상 | `ls -t data/backups/dam_*.dump` → 두 번째 파일로 재시도 |
| 썸네일 복원 후 깨진 파일 | `rsync -a --checksum` 으로 재동기화 |
| 전체 복구 실패 | 임베딩 재생성: `python ingest/clip_worker.py` (약 8분/160k) |

---

## 4. 데이터 손실 윈도

| 대상 | 백업 주기 | 최대 손실 |
|------|----------|----------|
| DB (메타·임베딩·태그) | 매일 1회 | **최대 24시간** |
| 썸네일 | 매주 1회 | **최대 7일** |
| 모델 파일 | 1회 (변경 없음) | HuggingFace에서 재다운로드 가능 |

**주의:** 썸네일은 원본에서 재생성 가능하나 약 20분 소요. 긴급 복구 시 임베딩 재생성(~8분)이 우선.
