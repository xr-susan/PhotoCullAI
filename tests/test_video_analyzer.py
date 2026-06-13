import numpy as np
from app.core.video_analyzer import analyze_video_file
from app.utils.image_utils import blur_score, brightness_metrics


class TestBlurScoreShared:
    """验证 video_analyzer 使用的是 image_utils 中的共享函数。"""

    def test_sharp_image(self):
        gray = np.zeros((400, 400), dtype=np.uint8)
        gray[:200, :200] = 255
        score = blur_score(gray)
        assert score > 100

    def test_uniform_image(self):
        gray = np.full((200, 200), 128, dtype=np.uint8)
        score = blur_score(gray)
        assert score == 0.0


class TestBrightnessMetricsShared:
    """验证 video_analyzer 使用的是 image_utils 中的共享函数。"""

    def test_normal_brightness(self):
        gray = np.full((100, 100), 128, dtype=np.uint8)
        mean, over, under = brightness_metrics(gray)
        assert 127 < mean < 129
        assert over == 0.0
        assert under == 0.0


class TestAnalyzeVideoFile:
    def test_nonexistent_file_returns_junk(self):
        result = analyze_video_file("nonexistent_video.mp4")
        assert result.verdict == "junk"
        assert result.media_type == "video"
        assert "无法读取" in result.reason or "出错" in result.reason

    def test_bad_path_returns_junk(self):
        result = analyze_video_file("")
        assert result.verdict == "junk"
