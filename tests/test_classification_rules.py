"""단위 테스트 — _classification_rules + _korean_norm"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingest._classification_rules import FOLDER_PATTERNS, FILENAME_KEYWORDS
from ingest._korean_norm import extract_korean, normalize_title


class TestFolderPatterns:
    def _match(self, path: str):
        return [(cls, sub) for pat, cls, sub, _ in FOLDER_PATTERNS if pat.search(path)]

    def test_content_design_poster(self):
        m = self._match("DAM/@디자인산출물_가로포스터/file.jpg")
        assert ("content", None) in m

    def test_content_vod(self):
        m = self._match("products/@디자인산출물_오픈VOD/img.png")
        assert ("content", None) in m

    def test_promotion_promo(self):
        m = self._match("2023/_프로모션_summer/banner.jpg")
        assert ("promotion", None) in m

    def test_promotion_home_banner(self):
        m = self._match("layout/01_첫화면빅배너/hero.jpg")
        assert ("promotion", "home_banner") in m

    def test_ui_service_menu(self):
        m = self._match("ui/_메뉴/icon.svg")
        assert ("ui_service", "menu") in m

    def test_composition_slice(self):
        m = self._match("분해/슬라이스/@슬라이스/part.png")
        assert ("composition", None) in m

    def test_draft(self):
        m = self._match("2024/시안/proposal.psd")
        assert ("draft", None) in m

    def test_movie_category(self):
        m = self._match("카탈로그/■영화/poster.jpg")
        assert ("content", "movie") in m

    def test_series_category(self):
        m = self._match("■시리즈/drama.jpg")
        assert ("content", "series") in m

    def test_no_match(self):
        m = self._match("random/folder/file.jpg")
        assert m == []


class TestFilenameKeywords:
    def test_seasonal(self):
        assert "추석" in FILENAME_KEYWORDS["seasonal"]

    def test_pricing(self):
        assert "할인" in FILENAME_KEYWORDS["pricing"]

    def test_promotion(self):
        assert "이벤트" in FILENAME_KEYWORDS["promotion"]

    def test_branding(self):
        assert "로고" in FILENAME_KEYWORDS["branding"]


class TestKoreanNorm:
    def test_extract_korean_basic(self):
        assert extract_korean("1760x600_조선정신과의사유세풍2.jpg") == ["조선정신과의사유세풍"]

    def test_extract_korean_multiple(self):
        result = extract_korean("케빈넌어디있어_2024.jpg")
        assert "케빈넌어디있어" in result

    def test_extract_korean_empty(self):
        assert extract_korean("NEXT_VOD_IMG.jpg") == []

    def test_normalize_title_removes_punct(self):
        assert normalize_title("조선 정신과의사, 유세풍!") == "조선정신과의사유세풍"

    def test_normalize_title_lowercase(self):
        assert normalize_title("Hello World") == "helloworld"
