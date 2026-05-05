# Step 3.1: branch-and-mount

> GitHub: 미생성 | Milestone: designfs1-mirror

## 읽어야 할 파일
- `docs/PRD.md` (Phase 3 정의: PSD 제외 ~1.48 TB)
- `db/migrations/001_init.sql` (realm `'designfs1_mirror'` 이미 valid)

## 작업
- `feature/phase3-designfs1` 브랜치 생성 후 체크아웃
- DESIGNFS1 SMB 마운트 정보 확인 (사용자 협력 필요):
  - 서버 주소·share 이름·계정/비밀번호
- 사용자가 직접 실행할 명령(예시):
  ```bash
  sudo mkdir -p /mnt/designfs1
  sudo mount -t cifs //<server>/<share> /mnt/designfs1 \
    -o username=<user>,password=<pw>,ro,uid=$(id -u),gid=$(id -g),iocharset=utf8
  ```
- `/etc/fstab` 영속 등록 (재부팅 후 자동 마운트):
  ```
  //<server>/<share> /mnt/designfs1 cifs ro,credentials=/etc/dam-credentials,uid=1000,gid=1000,iocharset=utf8 0 0
  ```
- 자격증명 파일 `/etc/dam-credentials` (chmod 600) 생성
- 마운트 후 검증: `ls /mnt/designfs1` 가능, 샘플 파일 `cat` 성공

## Acceptance Criteria
```bash
bash .claude/verify.sh 3.1
```
- `git rev-parse --abbrev-ref HEAD` == `feature/phase3-designfs1`
- `mountpoint -q /mnt/designfs1` 성공
- `grep designfs1 /etc/fstab` 매칭
- 샘플 파일 1개 read 성공

## 금지사항
- DESIGNFS1 에 write 마운트 하지 마라. 이유: 원본 불변 원칙 (ADR-001).
- 자격증명을 git 에 커밋하지 마라. `/etc/dam-credentials` 는 시스템 파일.
- 사용자 승인 없이 fstab 자동 수정하지 마라. 이유: 시스템 설정 변경은 가시성 + 권한 필요.
