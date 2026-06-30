"""verify.sh 4.3 전용 — 테스트 유저 생성 후 Bearer 토큰 출력."""
import os, sys
import psycopg

sys.path.insert(0, os.environ.get("PYTHONPATH", "."))
from api.auth import hash_password, issue_token

dsn = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")
username = sys.argv[1]   # verify43_adm or verify43_vw
role     = sys.argv[2]   # admin or viewer

with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM users WHERE username = %s", (username,)
        )
        cur.execute(
            "INSERT INTO users(username,password_hash,role) VALUES(%s,%s,%s) RETURNING id",
            (username, hash_password("x"), role),
        )
        uid = cur.fetchone()[0]
    conn.commit()

tok, _ = issue_token(uid)
print(tok)
