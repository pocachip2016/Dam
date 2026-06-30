# nfs-poc 2-PC 토폴로지 개정안 (nfs-poc.6~10)

> nfs-poc.1~5 는 단일 PC(PC-A) 전제로 완료. nfs-poc.6~9 는 **2-PC 분리**로 재정의한다.
> 결정(2026-06-30): **CLIP=PC-B 좋은 GPU / 적재=PC-B 운영 DB / NFS=PC-A 전용 / 연결=PC-A→PC-B SSH**.

## 1. 토폴로지

| | PC-A (중간 개발 PC) | PC-B |
|---|---|---|
| NFS 디자인 원본 (DESIGNFS/DESIGNFS1) | ✅ 마운트됨 | ❌ 불가 |
| PostgreSQL (운영 DB) | (로컬 docker = poc_sample 별개) | ✅ **적재 타깃** |
| GPU | 낮음 | 좋음 |
| 역할 | scan·hash·thumbnail (NFS 읽기) | clip-embed (GPU) + DB 호스트 |
| 연결 | `ssh` 로 PC-B 접속 가능 → | (수신) |

핵심 불변식:
- **NFS 원본 읽기 단계(scan/hash/thumbnail)는 PC-A 고정** — PC-B 는 원본 접근 불가.
- **CLIP 은 썸네일만 읽음(원본 불필요)** → PC-B GPU 로 분리 가능. 썸네일 ≈ 수 GB(전송 저렴).
- 교차통신은 전부 **PC-A → PC-B** 방향 → 단일 SSH 채널로 해결.

```
PC-A (NFS○ GPU↓)                                    PC-B (NFS✗ GPU↑ DB)
 ├ ssh -L 15433:localhost:5432  ───────────────────▶ postgres:5432
 ├ scan_ingest    (DAM_DSN=localhost:15433) ────────▶ assets/asset_storage (designfs1_mirror)
 ├ hash_worker    (DAM_DSN=localhost:15433) ────────▶ assets.sha256
 ├ thumbnail_worker(DAM_DSN=localhost:15433)
 │    └ THUMB_DIR 생성 (PC-A 로컬) ──rsync──────────▶ THUMB_DIR (PC-B, 동일 절대경로)
 └                                                    └ clip_worker (PC-B 로컬 DB+썸네일, GPU)
```

## 2. 공통 전제 (nfs-poc.6~9 가 의존, 1회 셋업)

### 2.1 SSH 포워드 터널 (PC-A 에서 실행)
PC-A 로컬 15432 는 자체 docker postgres(poc_sample) 가 점유 → 터널은 **15433** 사용.
```bash
ssh -fN -L 15433:localhost:5432  <PCB_USER>@<PCB_HOST>
# PC-B postgres 가 docker 호스트포트(예: 5432/15432)면 -L 15433:localhost:<그포트>
```
→ PC-A 워커는 `DAM_DSN=postgresql://<PCB_DBUSER>:<PCB_PW>@localhost:15433/<PCB_DB>`.

### 2.2 THUMB_DIR 절대경로 일치 (필수)
`thumbnail_path` 는 `THUMB_DIR` 기반 **절대경로**로 PC-B DB 에 저장된다. clip_worker(PC-B)가 그 경로를 그대로 읽으므로 **PC-A 와 PC-B 의 THUMB_DIR 절대경로가 동일해야** 한다.
- 채택 경로(파라미터): `DAM_THUMB_DIR` (예: `/data/dam/thumbnails`) — 양 PC 에 동일하게 생성.
- thumbnail_worker(PC-A): `THUMB_DIR=$DAM_THUMB_DIR` 로 로컬 생성.
- rsync: `rsync -a --info=progress2 $DAM_THUMB_DIR/ <PCB_USER>@<PCB_HOST>:$DAM_THUMB_DIR/`
- clip_worker(PC-B): `THUMB_DIR=$DAM_THUMB_DIR` 로 동일 경로 읽기.
- (대안) sshfs 직접쓰기 — 16만 소파일에 per-file 지연 큼 → **rsync 배치 권장**.
- (미래 ADR) 썸네일 경로를 상대경로 저장 + 런타임 THUMB_DIR 결합 → 다중호스트 무제약. PoC 범위 밖.

### 2.3 PC-B DB 준비 확인
운영 DB 라도 Dam 스키마/realm 이 있어야 적재 가능:
- 테이블 존재(assets, asset_storage, embeddings …), `pgvector` 확장, `designfs1_mirror` realm 사용 가능.
- 없으면 `db/migrations/*.sql` 를 PC-B 에 적용(별도 승인).
- realm 격리로 PC-B 기존 데이터 무침범.

## 3. 개정된 스텝 (id 유지, 실행구조만 2-PC 화)

### nfs-poc.6 scan-ingest (PC-A → PC-B DB)
```bash
# 전제: §2.1 터널 활성
DAM_REALM=designfs1_mirror \
POC_ROOT=/mnt/designfs1/dam_dev/11.NEXT_UI_2022_10월오픈 \
DAM_DSN='postgresql://<PCB_DBUSER>:<PCB_PW>@localhost:15433/<PCB_DB>' \
.venv/bin/python ingest/ingest_local.py
```
- verify: §2.1 터널 up + §2.3 PC-B 준비 + `asset_storage WHERE realm='designfs1_mirror'` count > 0 (≈167k 근사).

### nfs-poc.7 hash-dedup (PC-A → PC-B DB)
```bash
DAM_REALM=designfs1_mirror DAM_WORKERS=8 \
DAM_DSN='postgresql://...@localhost:15433/<PCB_DB>' \
.venv/bin/python ingest/hash_worker.py
```
- 대상은 DESIGNFS1 복사본(`/mnt/designfs1/...`, PC-A 읽기) → sha256 를 PC-B DB 에 기록.
- verify: `sha256 IS NOT NULL AND <>'ERROR'` (realm=designfs1_mirror) count > 0.

### nfs-poc.8 thumbnails (PC-A 생성 → rsync → PC-B)
```bash
DAM_REALM=designfs1_mirror THUMB_DIR=$DAM_THUMB_DIR WORKERS=4 \
DAM_DSN='postgresql://...@localhost:15433/<PCB_DB>' \
.venv/bin/python ingest/thumbnail_worker.py
rsync -a $DAM_THUMB_DIR/ <PCB_USER>@<PCB_HOST>:$DAM_THUMB_DIR/
```
- verify: `thumbnail_path IS NOT NULL`(realm) count > 0 + PC-B 에 썸네일 도착(원격 샘플 존재).

### nfs-poc.9 clip-embed (PC-B GPU)
```bash
# PC-B 에서 (git clone 동일 소스, venv, GPU)
MODEL=open_clip THUMB_DIR=$DAM_THUMB_DIR \
DAM_DSN='postgresql://<PCB_DBUSER>:<PCB_PW>@localhost:5432/<PCB_DB>' \
.venv/bin/python ingest/clip_worker.py
```
- PC-B 로컬 DB+썸네일 → 터널 불필요. clip-vit-b32 1모델로 PoC.
- verify: `embeddings JOIN asset_storage WHERE realm='designfs1_mirror'` count > 0.

### nfs-poc.10 search-validate + ADR + wrap
- API(PC-B 또는 PC-A→터널) 기동 → `/stats`(designfs1_mirror>0), `/search_text?...&realm=designfs1_mirror` 200+hits.
- **ADR 항목 추가**: ① 차세대 저장전략(물리=CAS해시/논리=DB뷰 3층) ② **2-PC 분리 아키텍처**(NFS브리지 PC-A + GPU/DB PC-B, SSH터널, THUMB_DIR 일치, 미래 상대경로 저장).
- 결과 `docs/nfs-poc-result.md`, TODO/CLAUDE.md 갱신, PR.

## 4. 실행에 필요한 파라미터 (step 6 전 확정)
- `PCB_HOST`, `PCB_USER` (SSH 접속)
- `PCB_DB`, `PCB_DBUSER`, `PCB_PW`, PC-B postgres 포트
- `DAM_THUMB_DIR` (양 PC 동일 절대경로)
- PC-B: repo 경로 + venv + GPU(torch/open_clip) 준비 여부
- PC-B DB 스키마/pgvector/realm 적용 여부 (없으면 마이그레이션 승인)

## 5.5 실측 확정 (2026-06-30) — 대폭 단순화

PC-B 점검 결과 **SSH 터널 불필요**로 확정:
- PC-B = Windows10 Enterprise, **RTX 4060 8GB**, hostname DESKTOP-VCQCEJG.
- PC-B Dam 스택 docker 가동 중: `dam_postgres 0.0.0.0:15432`, `dam_api :18000`, `dam_redis :16379` → **PC-A 에서 직접 도달**(처음 closed 였던 건 컨테이너 미기동 탓).
- PC-B dam_postgres: 21 테이블 + pgvector + `poc_sample` 161,030(임베딩 320,072) 보유, **`designfs1_mirror` 0건(비어있음)** → 적재 준비 완료. **DB/스키마 셋업 불필요.**
- SSH 키 인증 동작(`~/.ssh/dam_pcb_ed25519`, user=ktalpha). 터널 대신 **DB 직접 접속**:
  - `DAM_DSN=postgresql://dam:dam@222.112.179.161:15432/dam` (§2.1 터널 항목 폐기).
- CLIP(§nfs-poc.9): PC-B 가 Windows → `thumbnail_path`(PC-A Linux 절대경로) 불일치.
  → **PC-B 의 Linux GPU 도커 컨테이너**에서 clip_worker 실행 + 썸네일을 동일 절대경로로 마운트(step 8/9 확정). PC-B 는 이미 GPU 도커 운용(mediax-ollama 등).

## 5. 리스크
- **PC-B 스키마 부재** → scan 실패. step 6 전 §2.3 확인 필수.
- **THUMB_DIR 경로 불일치** → clip_worker 가 썸네일 못 찾음(FileNotFound→err). §2.2 절대경로 일치 강제.
- **터널 끊김** → 워커 DB 접속 실패. 세션 재개 시 §2.1 재실행.
- **DESIGNFS1 재마운트** → WSL 재시작 시 nfs-poc.2 마운트 재수행.
- 원본 불변: PC-A 는 DESIGNFS `-o ro`, 모든 단계 읽기전용.
