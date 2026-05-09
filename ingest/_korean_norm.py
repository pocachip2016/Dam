import re

KOREAN = re.compile(r'[가-힣]+')
NON_ALNUM = re.compile(r'[^0-9a-zA-Z가-힣]+')


def extract_korean(text: str) -> list[str]:
    """파일명에서 한글 substring 추출 — filename_tokens 토큰화 깨짐 회피."""
    return KOREAN.findall(text)


def normalize_title(text: str) -> str:
    """공백/구두점 제거 후 소문자."""
    return NON_ALNUM.sub('', text).lower()
