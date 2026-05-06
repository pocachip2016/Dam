"""Role keyword dictionary: Korean/English token → role label."""

ROLE_KEYWORDS: dict[str, list[str]] = {
    "poster": [
        "poster", "포스터", "pstr",
    ],
    "banner": [
        "banner", "배너", "bnr", "ban",
    ],
    "keyart": [
        "keyart", "key_art", "key-art", "키아트", "keyvisual", "key_visual", "kv",
    ],
    "thumbnail": [
        "thumbnail", "thumb", "썸네일", "tn", "thm",
    ],
    "background": [
        "background", "bg", "배경", "backdrop",
    ],
    "logo": [
        "logo", "로고", "ci", "bi",
    ],
    "detail": [
        "detail", "디테일", "dtl", "상세",
    ],
}

# Flat token → role lookup (built at import time)
TOKEN_TO_ROLE: dict[str, str] = {
    token: role
    for role, tokens in ROLE_KEYWORDS.items()
    for token in tokens
}
