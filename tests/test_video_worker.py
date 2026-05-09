"""M.4 video_worker 단위 테스트 — DB/파일 불필요."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingest.video_worker import _classify_video, VIDEO_EXTS


class TestClassifyVideo:
    def test_composition_default(self):
        cls, sub, conf, method = _classify_video("/random/folder/", "video.mp4")
        assert cls == "composition"
        assert sub == "video"
        assert method == "rule"

    def test_promotion_folder(self):
        cls, sub, conf, method = _classify_video("/2024/_프로모션_summer/", "banner.mp4")
        assert cls == "promotion"
        assert method == "folder_pattern"

    def test_content_vod_folder(self):
        cls, sub, conf, method = _classify_video("/@디자인산출물_오픈VOD/", "teaser.mp4")
        assert cls == "content"
        assert method == "folder_pattern"

    def test_home_banner_folder(self):
        cls, sub, conf, method = _classify_video("/01_첫화면빅배너/", "hero.mp4")
        assert cls == "promotion"
        assert sub == "home_banner"

    def test_draft_folder(self):
        cls, sub, conf, method = _classify_video("/시안/review/", "draft.mp4")
        assert cls == "draft"


class TestVideoExts:
    def test_mp4_in_set(self):
        assert ".mp4" in VIDEO_EXTS

    def test_mov_in_set(self):
        assert ".mov" in VIDEO_EXTS

    def test_mkv_in_set(self):
        assert ".mkv" in VIDEO_EXTS

    def test_jpg_not_in_set(self):
        assert ".jpg" not in VIDEO_EXTS


class TestDurationFallback:
    def test_missing_file_returns_none(self):
        from ingest.video_worker import _get_duration_ms
        result = _get_duration_ms("/nonexistent/path/video.mp4")
        assert result is None
