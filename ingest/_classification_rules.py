import re
from typing import Optional

# (regex, class, sub_class, confidence)
FOLDER_PATTERNS: list[tuple[re.Pattern, str, Optional[str], float]] = [
    (re.compile(r'@?디자인산출물_(가로포스터|단편상세|오픈VOD)'), 'content',     None,          0.95),
    (re.compile(r'(_프로모션_|기획전|캠페인|03_프로모션_콘텐츠유형)'), 'promotion', None,          0.92),
    (re.compile(r'(01_첫화면빅배너|고도화배너)'),                   'promotion',  'home_banner', 0.90),
    (re.compile(r'(_메뉴|컨테이너_메뉴)'),                          'ui_service', 'menu',        0.95),
    (re.compile(r'(슬라이스|@슬라이스|03_IMG)'),                   'composition', None,          0.90),
    (re.compile(r'(시안|draft|wip|^old$)'),                        'draft',      None,          0.85),
    (re.compile(r'■영화'),                                          'content',    'movie',       0.85),
    (re.compile(r'■(해외|국내)?시리즈'),                            'content',    'series',      0.85),
]

FILENAME_KEYWORDS: dict[str, list[str]] = {
    'seasonal':  ['추석','설날','크리스마스','여름','겨울','봄','가을','신년','연말','발렌타인','할로윈','명절','구정','어버이날'],
    'pricing':   ['할인','세일','쿠폰','특가','1+1','sale','discount'],
    'promotion': ['이벤트','캠페인','마케팅','프로모','광고','기획전','특별전'],
    'branding':  ['로고','logo','심볼','CI','BI'],
}
