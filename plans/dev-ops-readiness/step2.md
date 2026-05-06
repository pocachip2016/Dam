# Step 4.2: auth

> GitHub: 미생성 | Milestone: ops-readiness

## 읽어야 할 파일
- `api/main.py` (FastAPI app entry)
- `api/search.py`, `api/tags.py`, `api/collections.py` (Phase 3 의 X-User placeholder)

## 작업
- 마이그레이션 `db/migrations/006_users.sql`:
  ```sql
  CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,                 -- argon2 또는 bcrypt
    role          TEXT NOT NULL CHECK (role IN ('admin','editor','viewer')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
  );

  CREATE TABLE api_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    name        TEXT,
    expires_at  TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  ```
- 인증 메커니즘: API key (`Authorization: Bearer <token>`)
- `api/auth.py`:
  - `hash_password(plain) -> str` (argon2)
  - `verify_password(plain, hash) -> bool`
  - `issue_token(user_id) -> (raw_token, db_hash)` — raw 는 1회만 노출
  - FastAPI dependency `require_user(min_role: str)`:
    - viewer < editor < admin
    - 헤더 추출 → token_hash 조회 → 사용자/role 확인 → 401/403
- 초기 admin 생성 CLI: `scripts/create_user.py`
  ```bash
  python scripts/create_user.py --username admin --role admin --password-stdin
  ```
- 기존 endpoints 에 의존성 부착:
  - `/search_text`, `/similar`, `/stats`, `/filename_search` → `require_user('viewer')`
  - `/tags` POST/DELETE, `/collections` mutation → `require_user('editor')`
  - `/admin/*` (Step 4.3) → `require_user('admin')`
- UI:
  - `api/static/login.html` — username/password → POST `/auth/login` → token → localStorage
  - 모든 fetch 에 Authorization 헤더 자동 부착 (`api/static/app.js` 공통 모듈)
  - 401 응답 → login 페이지 redirect
  - X-User placeholder (Phase 3) 코드 제거

## Acceptance Criteria
```bash
bash .claude/verify.sh 4.2
```
- 시나리오:
  - anonymous `/search_text` → 401
  - 잘못된 token → 401
  - viewer token + POST `/tags` → 403
  - editor token + POST `/tags` → 201
  - admin token + `/admin/workers` → 200 (Step 4.3 endpoint)
- `users` row 존재, password 평문 컬럼 없음
- UI 미인증 진입 시 login 페이지로 redirect

## 금지사항
- password 평문 저장 금지. 이유: 보안. argon2/bcrypt only.
- token 을 cookie 에 저장하지 마라. 이유: CSRF 표면. localStorage + Authorization 헤더.
- `/static/login.html` 을 인증 게이트 뒤에 두지 마라. 이유: 무한 redirect.
- 기존 endpoint URL/시그니처 변경 금지 (의존성만 추가). 이유: UI 호환.
- Phase 3 의 X-User 헤더 처리 코드 잔존 금지. 이유: 인증 우회 표면.
