# Step 4.G.1: guard-script

> GitHub: 미생성 | Milestone: db-init-guard

## 읽어야 할 파일
- `docker-compose.yml`
- 사건 컨텍스트: 5/7 09:18 PG_VERSION birth time = 컨테이너 startup, RestartCount=0 → silent initdb 로 161k assets 유실

## 작업
- `scripts/postgres_entrypoint_guard.sh` 신규 작성:
  - shebang `#!/usr/bin/env bash` + `set -euo pipefail`
  - `/var/lib/postgresql/data/PG_VERSION` 존재 여부 체크
  - **존재** → `exec /usr/local/bin/docker-entrypoint.sh "$@"` (정상 패스스루)
  - **부재 + `DAM_ALLOW_INIT=yes`** → 패스스루 (의도된 fresh init 허용; 컨테이너 logs 에 1줄 경고 출력)
  - **부재 + flag 없음** → stderr 로 명확한 다중행 에러 출력 후 `exit 1`
    - 에러 메시지에 포함: 데이터 유실 가능성 / 백업 위치 (`data/backups/`) / 의도된 init 시 `DAM_ALLOW_INIT=yes` 사용법
- `chmod +x` 적용

## Acceptance Criteria
```bash
bash .claude/verify.sh 4.G.1
```
- 파일 존재 + executable
- `bash -n scripts/postgres_entrypoint_guard.sh` 통과 (syntax OK)
- shebang + `set -euo pipefail` 포함
- `DAM_ALLOW_INIT` 키워드 grep 매치

## 금지사항
- container 재시작 / pg_data 변경 / docker-compose.yml 수정 금지. 이유: 이 step 은 스크립트 단독 작성만 다룸. 통합은 4.G.2.
- bash 외 다른 언어(python 등) 사용 금지. 이유: postgres 컨테이너 안에서 실행되는데 bash 외 의존성 추가 부담.
