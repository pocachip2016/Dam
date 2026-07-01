"""
source_profile — realm → 파싱 프로파일 로더.

source_profiles 테이블에서 realm의 profile_key·folder_depth·parse_config를 읽어 반환.
realm 미등록 시 안전 기본값(generic)으로 폴백하고 경고를 남긴다.
"""
import logging
import os
from typing import TypedDict

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    raise SystemExit("psycopg 미설치")

log = logging.getLogger(__name__)

DB_DSN = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")

_FALLBACK: "SourceProfile" = {
    "realm": "__unknown__",
    "profile_key": "generic",
    "folder_depth": 2,
    "parse_config": {},
}


class SourceProfile(TypedDict):
    realm: str
    profile_key: str
    folder_depth: int
    parse_config: dict


def get_profile(realm: str) -> SourceProfile:
    """DB에서 realm 프로파일 조회. 미등록 realm은 generic 폴백."""
    try:
        with psycopg.connect(DB_DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT realm, profile_key, folder_depth, parse_config "
                    "FROM source_profiles WHERE realm = %s",
                    (realm,),
                )
                row = cur.fetchone()
    except Exception as exc:
        log.warning("source_profile: DB 조회 실패 (%s) — generic 폴백. 오류: %s", realm, exc)
        return {**_FALLBACK, "realm": realm}

    if row is None:
        log.warning("source_profile: 미등록 realm '%s' — generic 폴백", realm)
        return {**_FALLBACK, "realm": realm}

    return SourceProfile(
        realm=row["realm"],
        profile_key=row["profile_key"],
        folder_depth=row["folder_depth"],
        parse_config=row["parse_config"] or {},
    )


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    target = sys.argv[1] if len(sys.argv) > 1 else "poc_sample"
    print(get_profile(target))
