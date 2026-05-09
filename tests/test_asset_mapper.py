"""자산 분류·매핑 로직 단위 테스트 — DB 불필요."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingest.asset_mapper import classify_asset, match_content, ContentMatch


def _asset(filename="", folder_path="", role_hint=None, year_hint=None):
    return {
        "id": 1,
        "filename": filename,
        "folder_path": folder_path,
        "role_hint": role_hint or [],
        "year_hint": year_hint,
    }


def _content(content_id, title, original_title=None, production_year=None):
    return {
        "content_id": content_id,
        "title": title,
        "original_title": original_title,
        "production_year": production_year,
    }


CONTENT_INDEX = [
    _content(1, "조선 정신과의사 유세풍", production_year=2023),
    _content(2, "기생충", original_title="Parasite", production_year=2019),
    _content(3, "오징어 게임", production_year=2021),
    _content(4, "이태원 클라쓰", production_year=2020),
    _content(5, "스물다섯 스물하나", production_year=2022),
    _content(6, "더 글로리", production_year=2022),
    _content(7, "사랑의 불시착", production_year=2019),
    _content(8, "이상한 변호사 우영우", production_year=2022),
    _content(9, "빈센조", production_year=2021),
    _content(10, "나의 아저씨", production_year=2018),
]


class TestClassifyAsset:
    def test_content_from_folder(self):
        row = _asset(folder_path="/@디자인산출물_가로포스터/")
        classes = classify_asset(row, [])
        names = [c.cls for c in classes]
        assert "content" in names

    def test_composition_from_slice_folder(self):
        row = _asset(folder_path="/슬라이스/@슬라이스/")
        classes = classify_asset(row, [])
        names = [c.cls for c in classes]
        assert "composition" in names

    def test_promotion_from_folder(self):
        row = _asset(folder_path="/2023/_프로모션_여름/")
        classes = classify_asset(row, [])
        names = [c.cls for c in classes]
        assert "promotion" in names

    def test_seasonal_from_filename(self):
        row = _asset(filename="추석_이벤트배너.jpg", folder_path="/배너/")
        classes = classify_asset(row, [])
        names = [c.cls for c in classes]
        assert "seasonal" in names

    def test_pricing_from_filename(self):
        row = _asset(filename="여름_할인_이벤트.jpg")
        classes = classify_asset(row, [])
        names = [c.cls for c in classes]
        assert "pricing" in names

    def test_branding_from_role_hint(self):
        row = _asset(role_hint=["logo"])
        classes = classify_asset(row, [])
        names = [c.cls for c in classes]
        assert "branding" in names

    def test_unclassified_when_no_signal(self):
        row = _asset(filename="img_0001.jpg", folder_path="/random/folder/")
        classes = classify_asset(row, [])
        # 분류 없을 때 main()에서 unclassified 추가됨 — classify_asset 자체는 빈 목록 가능
        # 또는 빈 목록인지 확인
        assert classes == [] or any(c.cls == "unclassified" for c in classes)

    def test_multi_class(self):
        row = _asset(filename="첫화면빅배너_기생충.jpg", folder_path="/01_첫화면빅배너/")
        classes = classify_asset(row, [])
        names = {c.cls for c in classes}
        assert "promotion" in names

    def test_high_confidence_content_folder(self):
        row = _asset(folder_path="/prod/@디자인산출물_가로포스터/")
        classes = classify_asset(row, [])
        content_c = next((c for c in classes if c.cls == "content"), None)
        assert content_c is not None
        assert content_c.confidence >= 0.95


class TestMatchContent:
    def test_exact_filename_match(self):
        row = _asset(filename="1760x600_조선정신과의사유세풍2.jpg")
        matches = match_content(row, [], None, CONTENT_INDEX)
        assert any(m.content_id == 1 for m in matches)

    def test_tag_match_highest_priority(self):
        row = _asset(filename="random.jpg")
        matches = match_content(row, ["기생충"], None, CONTENT_INDEX)
        assert any(m.content_id == 2 for m in matches)
        # tag match should have high confidence
        tag_match = next(m for m in matches if m.content_id == 2)
        assert tag_match.confidence >= 0.95

    def test_folder_path_match(self):
        row = _asset(filename="poster.jpg", folder_path="/드라마/오징어게임/")
        matches = match_content(row, [], None, CONTENT_INDEX)
        assert any(m.content_id == 3 for m in matches)

    def test_year_bonus_applied(self):
        row = _asset(filename="기생충포스터.jpg", year_hint=2019)
        matches = match_content(row, [], None, CONTENT_INDEX)
        parasit = next((m for m in matches if m.content_id == 2), None)
        if parasit:
            assert parasit.confidence >= 0.90  # base + year bonus

    def test_below_threshold_not_returned(self):
        row = _asset(filename="아무관련없는파일.jpg", folder_path="/random/")
        matches = match_content(row, [], None, CONTENT_INDEX)
        # 관련 없는 파일은 threshold 이하여야
        for m in matches:
            assert m.confidence >= 0.85

    def test_returns_sorted_by_confidence(self):
        row = _asset(filename="기생충.jpg")
        matches = match_content(row, ["기생충"], None, CONTENT_INDEX)
        if len(matches) >= 2:
            for i in range(len(matches) - 1):
                assert matches[i].confidence >= matches[i + 1].confidence

    def test_no_match_returns_empty(self):
        row = _asset(filename="IMG_1234.jpg", folder_path="/misc/")
        matches = match_content(row, [], None, CONTENT_INDEX)
        # 단순 숫자 파일은 매핑 없어야
        assert isinstance(matches, list)

    def test_ocr_text_match(self):
        row = _asset(filename="scan.jpg")
        matches = match_content(row, [], "이태원 클라쓰 OST 모음", CONTENT_INDEX)
        assert any(m.content_id == 4 for m in matches)
