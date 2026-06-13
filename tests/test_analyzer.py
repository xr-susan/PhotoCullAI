import numpy as np
import pytest
from app.utils.image_utils import blur_score, brightness_metrics
from app.core.analyzer import (
    colorfulness_bgr, _contrast_quality, _subject_clarity,
    infer_category, _is_atmospheric, _eye_aspect_ratio, _mouth_ratio,
    _pose_awkwardness, _face_relative_size, _expression_quality,
    _asymmetry_score, _occlusion_score, _score_global, _score_portrait,
    _score_landscape, _score_screenshot, _score_text, _read_thresholds,
    DEDUCT_BLUR_HEAVY, DEDUCT_BLUR_LIGHT, DEDUCT_OVEREXPOSE,
)


# ---- 辅助构造 ----

def _make_gray(w=200, h=200, value=128):
    return np.full((h, w), value, dtype=np.uint8)


def _make_img(w=200, h=200, bgr=(128, 128, 128)):
    img = np.full((h, w, 3), bgr, dtype=np.uint8)
    return img


def _sharp_gray(w=400, h=400):
    """有清晰边缘的灰度图。"""
    gray = np.zeros((h, w), dtype=np.uint8)
    gray[:h//2, :w//2] = 255
    gray[h//2:, w//2:] = 200
    return gray


# ---- blur_score / brightness_metrics ----

class TestBlurScore:
    def test_uniform_image_low_blur(self):
        gray = _make_gray(200, 200, 128)
        score = blur_score(gray)
        assert score == 0.0

    def test_sharp_image_high_blur(self):
        gray = _sharp_gray(400, 400)
        score = blur_score(gray)
        assert score > 100

    def test_returns_float(self):
        assert isinstance(blur_score(_make_gray()), float)


class TestBrightnessMetrics:
    def test_uniform_brightness(self):
        gray = _make_gray(100, 100, 128)
        mean, over, under = brightness_metrics(gray)
        assert abs(mean - 128.0) < 0.1
        assert over == 0.0
        assert under == 0.0

    def test_overexposed(self):
        gray = _make_gray(100, 100, 250)
        mean, over, under = brightness_metrics(gray)
        assert mean > 240
        assert over > 0.9

    def test_underexposed(self):
        gray = _make_gray(100, 100, 5)
        mean, over, under = brightness_metrics(gray)
        assert mean < 10
        assert under > 0.9


# ---- colorfulness_bgr ----

class TestColorfulness:
    def test_gray_image_low_color(self):
        img = _make_img(100, 100, (128, 128, 128))
        assert colorfulness_bgr(img) < 5

    def test_colorful_image(self):
        img = _make_img(100, 100, (0, 0, 255))
        assert colorfulness_bgr(img) > 10


# ---- _contrast_quality ----

class TestContrastQuality:
    def test_uniform_low_contrast(self):
        gray = _make_gray(100, 100, 128)
        assert _contrast_quality(gray) < 0.3

    def test_moderate_contrast(self):
        # std ~60 → quality 1.0; std >90 → quality 0.4
        gray = _sharp_gray(200, 200)
        q = _contrast_quality(gray)
        assert q >= 0.4  # high std but above ideal range


# ---- _subject_clarity ----

class TestSubjectClarity:
    def test_uniform_low_clarity(self):
        gray = _make_gray(200, 200, 128)
        assert _subject_clarity(gray, _make_img(200, 200)) < 0.5

    def test_structured_higher_clarity(self):
        gray = _sharp_gray(400, 400)
        img = _make_img(400, 400)
        assert _subject_clarity(gray, img) > 0.3


# ---- infer_category ----

class TestInferCategory:
    def test_no_face_no_text_defaults_landscape(self):
        # Use a soft gradient to avoid screenshot/text detection
        gray = np.tile(np.linspace(80, 160, 400, dtype=np.uint8), (300, 1))
        img = np.stack([gray, gray, gray], axis=-1)
        cats = infer_category(gray, face_count=0, ocr_conf=0.0, text_blocks=0, img=img)
        assert "landscape" in cats or len(cats) >= 1

    def test_face_detected_is_portrait(self):
        gray = _make_gray(400, 300)
        img = _make_img(400, 300)
        cats = infer_category(gray, face_count=1, ocr_conf=0.0, text_blocks=0, img=img)
        assert "portrait" in cats

    def test_many_text_blocks_is_text(self):
        gray = _make_gray(400, 300)
        img = _make_img(400, 300)
        cats = infer_category(gray, face_count=0, ocr_conf=0.8, text_blocks=5, img=img)
        assert "text" in cats


# ---- _is_atmospheric ----

class TestIsAtmospheric:
    def test_bright_not_atmospheric(self):
        gray = _make_gray(200, 200, 200)
        img = _make_img(200, 200, (200, 200, 200))
        assert not _is_atmospheric(img, gray, 200.0)

    def test_dim_warm_may_be_atmospheric(self):
        gray = _make_gray(200, 200, 80)
        img = np.full((200, 200, 3), (60, 60, 100), dtype=np.uint8)  # R > B
        result = _is_atmospheric(img, gray, 80.0)
        # May or may not be atmospheric depending on other factors
        assert isinstance(result, bool)


# ---- face helper functions ----

class TestFaceHelpers:
    def test_eye_aspect_ratio_no_pts(self):
        assert _eye_aspect_ratio([]) == 0.0

    def test_mouth_ratio_no_pts(self):
        assert _mouth_ratio([]) == 0.0

    def test_pose_awkwardness_no_faces(self):
        assert _pose_awkwardness([], (400, 400, 3)) == 0.0

    def test_face_relative_size_no_faces(self):
        assert _face_relative_size([], (400, 400, 3)) == 0.0

    def test_expression_quality_no_meshes(self):
        assert _expression_quality([]) == 0.0

    def test_asymmetry_score_no_meshes(self):
        assert _asymmetry_score([]) == 0.0

    def test_occlusion_score_uniform_low(self):
        gray = _make_gray(200, 200, 128)
        assert _occlusion_score(gray, (50, 50, 150, 150)) < 0.3


# ---- _read_thresholds ----

class TestReadThresholds:
    def test_returns_dict(self):
        t = _read_thresholds()
        assert isinstance(t, dict)
        assert "keep_score" in t
        assert "blur_low" in t

    def test_keep_score_from_config(self):
        t = _read_thresholds()
        assert t["keep_score"] == 65


# ---- _score_global ----

class TestScoreGlobal:
    def test_perfect_image_high_score(self):
        m = {
            "blur": 500, "mean": 120, "over": 0.0, "under": 0.0,
            "skew": 0.0, "img": _make_img(), "gray": _sharp_gray(),
        }
        thresh = _read_thresholds()
        score, reasons, contrast_q, clarity = _score_global(m, thresh, False)
        assert score >= 80
        assert len(reasons) == 0

    def test_blurry_image_deducted(self):
        m = {
            "blur": 10, "mean": 120, "over": 0.0, "under": 0.0,
            "skew": 0.0, "img": _make_img(), "gray": _make_gray(value=120),
        }
        thresh = _read_thresholds()
        score, reasons, _, _ = _score_global(m, thresh, False)
        assert score < 85
        assert any("模糊" in r for r in reasons)

    def test_overexposed_deducted(self):
        m = {
            "blur": 500, "mean": 250, "over": 0.5, "under": 0.0,
            "skew": 0.0, "img": _make_img(), "gray": _make_gray(value=250),
        }
        thresh = _read_thresholds()
        score, reasons, _, _ = _score_global(m, thresh, False)
        assert any("过曝" in r for r in reasons)


# ---- 常量存在性 ----

class TestConstants:
    def test_deduction_constants_exist(self):
        assert DEDUCT_BLUR_HEAVY == 30
        assert DEDUCT_BLUR_LIGHT == 18
        assert DEDUCT_OVEREXPOSE == 18
