# Step 5: nas-mount

> GitHub: #6 | Milestone: server-migration

## 결과 요약 (2026-04-27 완료)

| 항목 | 값 |
|---|---|
| DESIGNFS share | `//designfs.ktalpha.com/DESIGNFS` → `/mnt/designfs` (ro) |
| DESIGNFS1 share | `//designfs.ktalpha.com/DESIGNFS1` → `/mnt/designfs1` (ro) |
| 자격증명 | `~/.smbcredentials` (chmod 600), domain=WORKGROUP 필수 |
| poc_sample 위치 | **`D:\Work\dam_poc_sample`** (= WSL `/mnt/d/Work/dam_poc_sample`) |
| poc_sample 원본 | `/mnt/designfs/디자인파트/11.NEXT_UI_2022_10월오픈` |
| 제외 룰 | `*.psd`, `*.psb`, `*.zip`, `Thumbs.db`, `.DS_Store`, `*.lnk`, `desktop.ini` |
| rsync 결과 | 161,096 파일 / 58.01 GB / 약 3시간 / exit 0 |
| 디렉토리 보존 | 11개 서브폴더 모두 (`@디자인산출물_*`, `■시연용...`, `00_가이드` 등) |

## 사전 점검 (수행)

| 항목 | 결과 |
|---|---|
| DNS | `designfs.ktalpha.com` → `192.168.181.22` ✅ |
| 445 포트 (SMB) | 도달 가능 ✅ |
| `mount.cifs` | 설치 완료 ✅ |
| 자격증명 | 사용자 직접 작성 (보안상 plan 파일에 비기록) |

## 작업 (수행 명령)

### ① cifs-utils 설치
```bash
sudo apt update && sudo apt install -y cifs-utils
```

### ② 자격증명 파일 작성 (`~/.smbcredentials`, chmod 600)
```bash
# username, password, domain 3줄. domain 필수 (없으면 STATUS_LOGON_FAILURE).
# 형식: LF only (CRLF 면 인증 실패).
cat > ~/.smbcredentials <<'EOF'
username=<사용자명>
password=<비밀번호>
domain=WORKGROUP
EOF
chmod 600 ~/.smbcredentials
```

### ③ 마운트 (두 share)
```bash
sudo mkdir -p /mnt/designfs /mnt/designfs1

sudo mount -t cifs //designfs.ktalpha.com/DESIGNFS /mnt/designfs \
  -o credentials=$HOME/.smbcredentials,uid=$(id -u),gid=$(id -g),iocharset=utf8,vers=3.0,ro,nobrl

sudo mount -t cifs //designfs.ktalpha.com/DESIGNFS1 /mnt/designfs1 \
  -o credentials=$HOME/.smbcredentials,uid=$(id -u),gid=$(id -g),iocharset=utf8,vers=3.0,ro,nobrl
```

옵션 설명:
- `ro` — 읽기 전용 (ADR-001: 원본 NAS 불변 원칙)
- `iocharset=utf8` — 한글 파일명 정상 표시
- `vers=3.0` — SMB 3.0
- `nobrl` — byte-range lock 비활성화 (대형 파일 안정성)
- `uid/gid` — 현재 사용자 권한으로 접근

### ④ poc_sample 복사 (rsync)
```bash
mkdir -p /mnt/d/Work/dam_poc_sample

rsync -a --stats --prune-empty-dirs --info=progress2,stats2 \
  --exclude='*.psd' --exclude='*.PSD' \
  --exclude='*.psb' --exclude='*.PSB' \
  --exclude='Thumbs.db' --exclude='.DS_Store' \
  --exclude='*.lnk' --exclude='desktop.ini' \
  --exclude='*.zip' --exclude='*.ZIP' \
  "/mnt/designfs/디자인파트/11.NEXT_UI_2022_10월오픈/" \
  /mnt/d/Work/dam_poc_sample/
```

### ⑤ 검증
```bash
mountpoint -q /mnt/designfs && mountpoint -q /mnt/designfs1 && echo "BOTH OK"
find /mnt/d/Work/dam_poc_sample -type f | wc -l   # 161096
du -sh /mnt/d/Work/dam_poc_sample                  # ~55 GB (du block)
```

## Acceptance Criteria
```bash
bash .claude/verify.sh 1.5
```
- 두 share 모두 `mountpoint -q` 통과
- `/mnt/designfs/디자인파트/11.NEXT_UI_2022_10월오픈` 접근 가능
- `/mnt/d/Work/dam_poc_sample` 존재 + 파일 수 ≥ 80,000

## 결정 사항

### poc_sample 위치 — 로컬 D 드라이브 (B안)
`docs/scan-analysis-2.md`, `docs/scan-analysis-3.md` 분석을 바탕으로 다음 검토 후 D 드라이브 결정:

- (A) NAS 직접 스캔 — SMB metadata I/O latency (1000× ↑) 누적, hash/exif 워커 5–10× 느림
- (B) **로컬 D 드라이브** ← 선택. ext4 native 보다 약간 느리지만 PoC 충분, 윈도우 탐색기 검수 가능, phase 2 와 동일 디스크 클래스
- (C) NAS designfs1 sub-folder — designfs1 도 NAS 자산이라 정책·소유 협의 필요, drvfs 메리트 없음

### 샘플 후보 — 11.NEXT_UI 폴더 전체 + exclude
서브폴더 추리는 대신 PSD/PSB/zip/노이즈 exclude 만으로 자연스럽게 60 GB / 16만 파일 → 디렉토리 구조 100% 보존.

## 확인 필요 사항 (다음 step 영향)

1. **마운트 영속화** — 이번 step 에서는 `/etc/fstab` 등록 안 함. 재부팅 후 재마운트 스크립트 필요. → backlog (`Step 1.7 이후 또는 별도 task`)
2. **drvfs metadata 성능** — Step 1.6 hash_worker 첫 실행 시 ext4 native 대비 5–10 분 추가 예상. 측정 후 phase 2 회귀 비교.
3. **realm 명** — verify.sh 1.6 의 `realm='poc_sample'` 그대로 유지.

## 금지사항
- 자격증명을 git 추적 파일/plan 파일/CLAUDE.md 에 적지 마라. 이유: 보안 민감정보.
- `rw` (쓰기) 옵션으로 마운트하지 마라. 이유: ADR-001 원본 불변 원칙.
- `/etc/fstab` 영속 등록 자동화하지 마라. 이유: 자격증명 노출 위험, 사용자 직접 결정.

## 트러블슈팅 (수행 중 만난 이슈)

| 증상 | 원인/해결 |
|---|---|
| `mount error(13): Permission denied` + `STATUS_LOGON_FAILURE` | 자격증명에 `domain=WORKGROUP` 누락 — 추가 후 통과 |
| `mount error(112): Host is down` | SMB 버전 불일치 — `vers=3.0` → `2.1` 또는 `1.0` 시도 |
| 한글 파일명 깨짐 | `iocharset=utf8` 누락 또는 `nounix` 옵션 추가 |
| `mount: only root can do that` | sudo 없이 mount 시도 — sudo 필요 |
| `smbclient -L` 만 실패하고 mount 는 성공 | IPC$ 권한 문제 — 무시 가능 |
