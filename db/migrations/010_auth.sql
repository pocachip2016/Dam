-- 010: auth — users + api_tokens (bearer token, role-based access)
--
-- viewer < editor < admin 위계. token 은 sha256(raw) 해시만 저장.
-- raw 는 issue_token() 반환 시 1회만 노출, 이후 복원 불가.

CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,           -- argon2id only, 평문 저장 금지
    role            TEXT NOT NULL CHECK (role IN ('admin', 'editor', 'viewer')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

CREATE TABLE api_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,        -- sha256(raw_token) hex, raw 비저장
    name        TEXT,
    expires_at  TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_api_tokens_user ON api_tokens(user_id);
CREATE INDEX idx_api_tokens_hash ON api_tokens(token_hash);

COMMENT ON TABLE users IS
    'Dam 사용자. password_hash = argon2id. role: viewer < editor < admin.';
COMMENT ON TABLE api_tokens IS
    'Bearer 토큰. token_hash = sha256(raw). raw 는 발급 시 1회만 노출.';
COMMENT ON COLUMN api_tokens.revoked_at IS
    'NULL = 유효. 폐기 시 now() 설정. DELETE 대신 revoke 권장 (감사 로그 보존).';
