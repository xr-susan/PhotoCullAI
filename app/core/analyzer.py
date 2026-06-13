import logging
import math
import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---- 评分扣分常量 ----
DEDUCT_BLUR_HEAVY = 30
DEDUCT_BLUR_LIGHT = 18
DEDUCT_BLUR_ATMO = 5
DEDUCT_OVEREXPOSE = 18
DEDUCT_UNDEREXPOSE = 15
DEDUCT_UNDEREXPOSE_ATMO = 3
DEDUCT_LOW_CONTRAST = 12
DEDUCT_NO_SUBJECT = 15
DEDUCT_WEAK_SUBJECT = 8
DEDUCT_NO_FACE = 40
DEDUCT_EYE_CLOSED = 30
DEDUCT_EYE_CLOSED_ATMO = 8
DEDUCT_POSE_SEVERE = 30
DEDUCT_POSE_BAD = 20
DEDUCT_POSE_SLIGHT = 10
DEDUCT_HEAD_TILT_SEVERE = 15
DEDUCT_HEAD_TILT_SLIGHT = 8
DEDUCT_EXPR_SEVERE = 30
DEDUCT_EXPR_BAD = 20
DEDUCT_EXPR_SLIGHT = 10
DEDUCT_ASYMMETRY = 15
DEDUCT_FACE_TINY = 25
DEDUCT_FACE_SMALL = 15
DEDUCT_FACE_BIG = 10
DEDUCT_OCCLUSION_SEVERE = 30
DEDUCT_OCCLUSION_MODERATE = 20
DEDUCT_OCCLUSION_SLIGHT = 10
DEDUCT_COLOR_FLAT = 10
DEDUCT_NO_DIMENSION = 8
DEDUCT_SKEW_LANDSCAPE = 20
DEDUCT_COLOR_FLAT_LANDSCAPE = 15
DEDUCT_COLOR_FLAT_ATMO = 3
DEDUCT_EMPTY_SCENE = 18
DEDUCT_SOFT_LANDSCAPE = 15
DEDUCT_SOFT_ATMO = 3
DEDUCT_NO_LAYERS = 10
DEDUCT_SCREENSHOT_BLUR = 15
DEDUCT_SCREENSHOT_OCR = 10
DEDUCT_TEXT_OCR_LOW = 15
DEDUCT_TEXT_SKEW = 18
DEDUCT_TEXT_REFLECTION = 12
DEDUCT_TEXT_BLUR = 20
DEDUCT_TEXT_BORDER = 8

from app.core.types import MediaResult
from app.utils.image_utils import safe_imread, resize_long_side, bgr_to_gray, blur_score, brightness_metrics
from app.utils.file_utils import is_image
from app.utils.config import get
from app.core.video_analyzer import analyze_video_file
from app.core.face_recognition import FaceRecognitionService, get_shared_face_app

try:
    from paddleocr import PaddleOCR
except Exception:
    PaddleOCR = None


class OCRService:
    def __init__(self):
        self.engine = None
        if PaddleOCR is not None:
            try:
                self.engine = PaddleOCR(
                    lang="ch",
                    use_textline_orientation=True,
                )
            except Exception:
                self.engine = None

    def run(self, img_bgr):
        if self.engine is None:
            return 0.0, 0
        try:
            res = self.engine.ocr(img_bgr, cls=True)
            if not res:
                return 0.0, 0
            lines = res[0] if isinstance(res, list) and len(res) == 1 else res
            if not lines:
                return 0.0, 0
            total_conf, cnt = 0.0, 0
            for item in lines:
                if not item or len(item) < 2:
                    continue
                conf = item[1][1] if isinstance(item[1], (list, tuple)) and len(item[1]) > 1 else item[1]
                try:
                    conf = float(conf)
                except Exception:
                    conf = 0.0
                total_conf += conf
                cnt += 1
            avg = total_conf / cnt if cnt else 0.0
            return round(avg, 4), cnt
        except Exception:
            return 0.0, 0


class FaceAnalyzer:
    def detect(self, img_bgr):
        """返回 (face_boxes, face_landmarks_106, pose_angle)"""
        app = get_shared_face_app()
        if app is None:
            return [], [], 0.0
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        except Exception:
            return [], [], 0.0

        h, w = img_bgr.shape[:2]
        face_boxes, face_meshes = [], []

        try:
            faces = app.get(rgb)
        except Exception:
            logger.debug("insightface 人脸检测异常", exc_info=True)
            return [], [], 0.0

        for face in faces:
            # 边界框
            x1, y1, x2, y2 = face.bbox.astype(int)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 > x1 and y2 > y1:
                face_boxes.append((x1, y1, x2, y2))

            # 106 点关键点（用于闭眼/张嘴检测）
            if hasattr(face, 'landmark_2d_106') and face.landmark_2d_106 is not None:
                pts = [(int(p[0]), int(p[1])) for p in face.landmark_2d_106]
                face_meshes.append(pts)

        # 姿态估计：用最大人脸的 5 关键点（双眼、鼻、嘴角）
        pose_angle = 0.0
        if faces:
            best = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
            if best.kps is not None and len(best.kps) >= 5:
                # kps: [左眼, 右眼, 鼻子, 左嘴角, 右嘴角]
                le, re = best.kps[0], best.kps[1]
                dx = re[0] - le[0]
                dy = re[1] - le[1]
                pose_angle = abs(math.degrees(math.atan2(dy, dx)))

        return face_boxes, face_meshes, pose_angle


class _LazySingleton:
    """延迟初始化单例，首次访问时才创建对象。"""
    def __init__(self, factory):
        self._factory = factory
        self._instance = None
    def get(self):
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

OCR = _LazySingleton(OCRService)
FACE = _LazySingleton(FaceAnalyzer)
FACE_REC = _LazySingleton(FaceRecognitionService)


def _eye_aspect_ratio(pts):
    """计算眼部纵横比（insightface 106 点关键点）。"""
    try:
        # 左眼：35=外角, 37=上中, 39=内角, 41=下中
        le = [np.array(pts[i], dtype=np.float32) for i in (35, 37, 39, 41)]
        left_ear = np.linalg.norm(le[1] - le[3]) / (np.linalg.norm(le[0] - le[2]) + 1e-6)
        # 右眼：89=外角, 91=上中, 93=内角, 95=下中
        re = [np.array(pts[i], dtype=np.float32) for i in (89, 91, 93, 95)]
        right_ear = np.linalg.norm(re[1] - re[3]) / (np.linalg.norm(re[0] - re[2]) + 1e-6)
        return float((left_ear + right_ear) / 2.0)
    except Exception:
        return 0.0


def _mouth_ratio(pts):
    """计算嘴部开合比（insightface 106 点关键点）。"""
    try:
        # 62=上唇中, 68=下唇中, 48=左嘴角, 54=右嘴角
        top = np.array(pts[62], dtype=np.float32)
        bot = np.array(pts[68], dtype=np.float32)
        left = np.array(pts[48], dtype=np.float32)
        right = np.array(pts[54], dtype=np.float32)
        return float(np.linalg.norm(top - bot) / (np.linalg.norm(left - right) + 1e-6))
    except Exception:
        return 0.0


def colorfulness_bgr(img):
    try:
        B, G, R = cv2.split(img.astype("float"))
        rg = np.abs(R - G)
        yb = np.abs(0.5 * (R + G) - B)
        std_rg, std_yb = np.std(rg), np.std(yb)
        mean_rg, mean_yb = np.mean(rg), np.mean(yb)
        return round(float(np.sqrt(std_rg**2 + std_yb**2) + 0.3 * np.sqrt(mean_rg**2 + mean_yb**2)), 2)
    except Exception:
        return 0.0


def _occlusion_score(gray, face_box):
    """检测人脸区域是否有物体遮挡。
    返回 0.0~1.0，1.0 表示完全被遮挡，0.0 表示无遮挡。"""
    try:
        x1, y1, x2, y2 = face_box
        h, w = gray.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 10 or y2 - y1 < 10:
            return 1.0
        roi = gray[y1:y2, x1:x2]
        # 检测人脸区域内的边缘密度——如果有物体遮挡，边缘会异常密集
        edges = cv2.Canny(roi, 50, 150)
        edge_density = float(np.mean(edges > 0))
        # 检测颜色一致性——遮挡物通常颜色与人脸差异大
        std = float(np.std(roi))
        # 边缘密度高 + 颜色方差大 = 可能有遮挡
        occlusion = min(1.0, edge_density * 3.0 + max(0, std - 50) / 100.0)
        return round(occlusion, 3)
    except Exception:
        return 0.0


def _subject_clarity(gray, img):
    """评估主体清晰度：视觉重心是否明确。
    返回 0.0~1.0，越高表示主体越清晰。"""
    try:
        h, w = gray.shape[:2]
        if h == 0 or w == 0:
            return 0.0
        # 用 Sobel 检测边缘强度分布
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_mag = np.sqrt(sobel_x**2 + sobel_y**2)
        # 把图像分成 3x3 网格，计算每个区域的边缘能量
        rh, rw = h // 3, w // 3
        energies = []
        for i in range(3):
            for j in range(3):
                region = edge_mag[i*rh:(i+1)*rh, j*rw:(j+1)*rw]
                energies.append(float(np.mean(region)))
        if not energies:
            return 0.0
        total = sum(energies)
        if total < 1e-6:
            return 0.0
        # 计算能量集中度——如果主体清晰，能量会集中在少数区域
        sorted_e = sorted(energies, reverse=True)
        top2_ratio = sum(sorted_e[:2]) / total
        # 越集中越好（主体明确）
        clarity = min(1.0, top2_ratio * 1.2)
        return round(clarity, 3)
    except Exception:
        return 0.0


def _contrast_quality(gray):
    """评估图像对比度质量。
    返回 0.0~1.0，越高越好。"""
    try:
        # 标准差衡量对比度
        std = float(np.std(gray))
        # 理想对比度标准差在 40~70 之间
        if std < 15:
            return 0.1  # 太灰，对比度极差
        if std < 30:
            return 0.3
        if std < 45:
            return 0.6
        if std <= 70:
            return 1.0
        if std <= 90:
            return 0.7
        return 0.4  # 对比度过高
    except Exception:
        return 0.5


def _face_relative_size(face_boxes, img_shape):
    """计算最大人脸相对于画面的比例。"""
    if not face_boxes:
        return 0.0
    h, w = img_shape[:2]
    total_area = h * w
    if total_area == 0:
        return 0.0
    max_area = max((x2-x1)*(y2-y1) for x1, y1, x2, y2 in face_boxes)
    return max_area / total_area


def _pose_awkwardness(face_boxes, img_shape):
    """检测人物姿势是否不协调。
    通过分析人脸在画面中的位置和比例判断。
    返回 0.0~1.0，越高表示姿势越不协调。"""
    if not face_boxes:
        return 0.0
    h, w = img_shape[:2]
    scores = []

    for x1, y1, x2, y2 in face_boxes:
        face_w = x2 - x1
        face_h = y2 - y1
        face_cx = (x1 + x2) / 2
        face_cy = (y1 + y2) / 2

        penalty = 0.0

        # 人脸过于靠边（被裁切或构图很差）
        margin_ratio = 0.08
        if face_cx < w * margin_ratio or face_cx > w * (1 - margin_ratio):
            penalty += 0.3  # 脸贴边
        if face_cy < h * margin_ratio or face_cy > h * (1 - margin_ratio):
            penalty += 0.2  # 脸贴顶/底

        # 人脸比例异常（过大=大头照不好看，过小=看不清）
        face_area_ratio = (face_w * face_h) / (h * w + 1e-6)
        if face_area_ratio > 0.45:
            penalty += 0.2  # 大头照，构图不好
        elif face_area_ratio < 0.02:
            penalty += 0.3  # 太小

        # 人脸宽高比异常（正常人脸宽高比约 0.6~0.9）
        if face_h > 0:
            aspect = face_w / face_h
            if aspect > 1.2 or aspect < 0.4:
                penalty += 0.2

        scores.append(min(1.0, penalty))

    return max(scores) if scores else 0.0


def _expression_quality(face_meshes, mouth_ratio_thresh=0.22):
    """分析表情管理质量。
    检测：张嘴、不对称表情、奇怪表情。
    返回 0.0~1.0，越高表示表情越差。"""
    if not face_meshes:
        return 0.0

    worst = 0.0
    for pts in face_meshes[:3]:
        penalty = 0.0
        mouth = _mouth_ratio(pts)
        ear = _eye_aspect_ratio(pts)

        # 张嘴程度
        if mouth > 0.35:
            penalty += 0.5  # 嘴张很大
        elif mouth > mouth_ratio_thresh:
            penalty += 0.25  # 微张嘴

        # 半闭眼
        if ear < 0.15 and ear > 0:
            penalty += 0.3

        # 眼睛完全闭合
        if ear < 0.08 and ear > 0:
            penalty += 0.4

        worst = max(worst, min(1.0, penalty))

    return worst


def _asymmetry_score(face_meshes):
    """检测面部不对称程度（可能表情奇怪）。
    返回 0.0~1.0。"""
    if not face_meshes:
        return 0.0

    worst = 0.0
    for pts in face_meshes[:1]:  # 只检测最大脸
        try:
            if len(pts) < 106:
                continue
            # 左右眼的纵坐标差异
            left_eye_y = np.mean([pts[35][1], pts[37][1], pts[39][1], pts[41][1]])
            right_eye_y = np.mean([pts[89][1], pts[91][1], pts[93][1], pts[95][1]])
            eye_diff = abs(left_eye_y - right_eye_y)

            # 左右嘴角的纵坐标差异
            left_mouth = pts[48]
            right_mouth = pts[54]
            mouth_diff = abs(left_mouth[1] - right_mouth[1])

            # 归一化
            face_height = max(1, abs(pts[0][1] - pts[16][1])) if len(pts) > 16 else 100
            eye_asym = eye_diff / face_height
            mouth_asym = mouth_diff / face_height

            if eye_asym > 0.08:
                worst = max(worst, 0.4)
            if mouth_asym > 0.06:
                worst = max(worst, 0.3)
            if eye_asym > 0.12 or mouth_asym > 0.1:
                worst = max(worst, 0.6)
        except Exception:
            pass

    return worst


def skew_score(gray):
    try:
        edges = cv2.Canny(gray, 60, 160)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=80,
            minLineLength=max(40, gray.shape[1] // 8), maxLineGap=12
        )
        if lines is None:
            return 0.0
        angles = []
        for l in lines[:300]:
            x1, y1, x2, y2 = l[0]
            ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if ang < -90: ang += 180
            if ang > 90: ang -= 180
            if abs(ang) <= 30:
                angles.append(ang)
        return round(float(abs(np.median(angles))), 2) if angles else 0.0
    except Exception:
        return 0.0


def _is_atmospheric(img, gray, mean_brightness):
    """检测是否为氛围感照片：低饱和度 + 暖色调 + 柔和光线"""
    try:
        h, w = gray.shape[:2]
        if h == 0 or w == 0:
            return False

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sat_mean = round(float(np.mean(hsv[:, :, 1])), 2)

        b_mean = round(float(np.mean(img[:, :, 0])), 2)
        r_mean = round(float(np.mean(img[:, :, 2])), 2)
        warm_tone = r_mean > b_mean + 5

        brightness_std = round(float(np.std(gray)), 2)
        is_dim = 40 < mean_brightness < 120

        over = round(float(np.mean(gray >= 240)), 4)
        under = round(float(np.mean(gray <= 15)), 4)
        soft_contrast = over < 0.05 and under < 0.15

        low_sat_warm = sat_mean < 80 and warm_tone
        soft_light = brightness_std < 55 and is_dim

        score = 0
        if low_sat_warm:
            score += 1
        if soft_light:
            score += 1
        if soft_contrast:
            score += 1
        if is_dim and warm_tone:
            score += 1

        return score >= 2
    except Exception:
        return False


def reflection_score(gray):
    try:
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = np.mean(blur) + 1.3 * np.std(blur)
        return float(np.mean(blur > min(255, thresh)))
    except Exception:
        return 0.0


def detect_screenshot(gray, img):
    """检测是否为截图：高对比度、规则边缘、纯色块"""
    try:
        h, w = gray.shape[:2]
        if h == 0 or w == 0:
            return False

        edges = cv2.Canny(gray, 100, 200)
        edge_density = float(np.mean(edges > 0))

        unique_colors = len(np.unique(gray // 16))

        horizontal_lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100,
            minLineLength=w // 3, maxLineGap=5
        )
        h_line_count = len(horizontal_lines) if horizontal_lines is not None else 0

        if edge_density > 0.05 and unique_colors < 100 and h_line_count > 3:
            return True
        if edge_density > 0.08 and unique_colors < 60:
            return True

        return False
    except Exception:
        return False


def infer_category(gray, face_count, ocr_conf, text_blocks, img):
    h, w = gray.shape[:2]
    if h == 0 or w == 0:
        return ["unknown"]

    aspect = round(w / max(h, 1), 4)
    edge_density = round(float(np.mean(cv2.Canny(gray, 80, 180) > 0)), 4)
    colorf = colorfulness_bgr(img)

    cats = []

    # 人像：检测到人脸就一定是人像
    if face_count >= 1:
        cats.append("portrait")

    # 截图：高对比度、规则边缘、纯色块
    if detect_screenshot(gray, img):
        cats.append("screenshot")

    # 文字：OCR 检测到多行文字或高置信度
    if text_blocks >= 3 or (ocr_conf > 0.45 and edge_density > 0.02 and aspect > 0.6):
        if "text" not in cats:
            cats.append("text")
    elif colorf < 5 and edge_density < 0.07:
        if "text" not in cats:
            cats.append("text")

    # 风景判断：宽幅或色彩丰富或低边缘密度
    # 如果已有人像，风景门槛降低（人像+风景场景）
    if "portrait" in cats:
        # 有人像的图，只要不是纯人像特写（色彩丰富或宽幅），就加风景
        if aspect > 1.0 and colorf > 6:
            if "landscape" not in cats:
                cats.append("landscape")
    else:
        # 无人像，标准风景判断
        if aspect > 1.15 and edge_density < 0.12 and colorf > 8:
            if "landscape" not in cats:
                cats.append("landscape")

    # 没有任何分类时默认风景
    if not cats:
        cats.append("landscape")

    return cats


def auto_rotate_image(img, gray):
    """检测画面歪斜角度并自动旋转矫正"""
    try:
        skew = skew_score(gray)
        if skew < 1.5:
            return img, 0.0

        # 用 HoughLines 检测主要线条角度
        edges = cv2.Canny(gray, 60, 160)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=80,
            minLineLength=max(40, gray.shape[1] // 8), maxLineGap=12
        )
        if lines is None:
            return img, 0.0

        angles = []
        for l in lines[:300]:
            x1, y1, x2, y2 = l[0]
            ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if ang < -90:
                ang += 180
            if ang > 90:
                ang -= 180
            if abs(ang) <= 30:
                angles.append(ang)

        if not angles:
            return img, 0.0

        median_angle = float(np.median(angles))
        if abs(median_angle) < 1.5:
            return img, median_angle

        h, w = img.shape[:2]
        center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        # 计算旋转后画布大小，避免裁切
        cos_a = abs(M[0, 0])
        sin_a = abs(M[0, 1])
        new_w = int(h * sin_a + w * cos_a)
        new_h = int(h * cos_a + w * sin_a)
        M[0, 2] += (new_w - w) / 2
        M[1, 2] += (new_h - h) / 2
        rotated = cv2.warpAffine(img, M, (new_w, new_h),
                                 flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REFLECT)
        return rotated, median_angle
    except Exception:
        return img, 0.0


def _load_and_preprocess(path):
    """加载并预处理图片，返回 (img, gray)。失败时抛异常。"""
    img = safe_imread(path)
    if img is None:
        raise ValueError("无法读取图片")
    img = resize_long_side(img)
    gray = bgr_to_gray(img)
    if gray is None or gray.size == 0:
        raise ValueError("图片数据损坏")
    return img, gray


def _read_thresholds():
    """从配置读取评分阈值。"""
    return {
        "keep_score": get("thresholds", "keep_score", 65),
        "blur_low": get("thresholds", "blur_low", 80),
        "blur_medium": get("thresholds", "blur_medium", 150),
        "eye_closed": get("thresholds", "portrait_eye_closed", 0.18),
        "landscape_skew": get("thresholds", "landscape_skew_deg", 3.5),
        "text_skew": get("thresholds", "text_skew_deg", 2.0),
        "over": get("thresholds", "overexposure", 0.18),
        "under": get("thresholds", "underexposure", 0.20),
    }


def _compute_metrics(img, gray):
    """计算全局质量指标。"""
    blur = blur_score(gray)
    mean, over, under = brightness_metrics(gray)
    skew = skew_score(gray)
    face_boxes, face_meshes, pose_angle = FACE.get().detect(img)
    face_count = max(len(face_boxes), len(face_meshes))
    ocr_conf, text_blocks = OCR.get().run(img)
    face_emb = FACE_REC.get().extract_embedding(img) if face_count >= 1 else None
    return {
        "blur": blur, "mean": mean, "over": over, "under": under,
        "skew": skew, "face_boxes": face_boxes, "face_meshes": face_meshes,
        "pose_angle": pose_angle, "face_count": face_count,
        "ocr_conf": ocr_conf, "text_blocks": text_blocks,
        "face_emb": face_emb,
    }


def _score_global(m, thresh, is_atmo):
    """全局质量评分（基准 85 分）。返回 (score, reasons)。"""
    score = 85.0
    reasons = []

    if m["blur"] < thresh["blur_low"]:
        score -= DEDUCT_BLUR_HEAVY
        reasons.append("明显模糊")
    elif m["blur"] < thresh["blur_medium"]:
        if is_atmo:
            score -= DEDUCT_BLUR_ATMO
            reasons.append("氛围感柔焦")
        else:
            score -= DEDUCT_BLUR_LIGHT
            reasons.append("轻微模糊")

    if m["over"] > thresh["over"]:
        score -= DEDUCT_OVEREXPOSE
        reasons.append("过曝")
    if m["under"] > thresh["under"]:
        if is_atmo:
            score -= DEDUCT_UNDEREXPOSE_ATMO
            reasons.append("氛围感暗调")
        else:
            score -= DEDUCT_UNDEREXPOSE
            reasons.append("欠曝")

    contrast_q = _contrast_quality(m["gray"])
    clarity = _subject_clarity(m["gray"], m["img"])

    if contrast_q < 0.3:
        score -= DEDUCT_LOW_CONTRAST
        reasons.append("对比度差，画面灰蒙")
    if clarity < 0.35:
        score -= DEDUCT_NO_SUBJECT
        reasons.append("主体不明确，构图散乱")
    elif clarity < 0.5:
        score -= DEDUCT_WEAK_SUBJECT
        reasons.append("主体不够突出")

    return score, reasons, contrast_q, clarity


def _score_portrait(m, thresh, base_score, base_reasons, is_atmo, contrast_q):
    """人像类别评分。返回 (score, reasons)。"""
    score = base_score
    reasons = list(base_reasons)

    if m["face_count"] == 0:
        score -= DEDUCT_NO_FACE
        reasons.append("未检测到清晰人脸")
        return score, reasons

    best_ear = min((_eye_aspect_ratio(pts) for pts in m["face_meshes"][:3]), default=999.0)
    if best_ear != 999.0 and best_ear < thresh["eye_closed"]:
        if is_atmo:
            score -= DEDUCT_EYE_CLOSED_ATMO
            reasons.append("氛围感半闭眼")
        else:
            score -= DEDUCT_EYE_CLOSED
            reasons.append("疑似闭眼")

    pose_bad = _pose_awkwardness(m["face_boxes"], m["img"].shape)
    if pose_bad > 0.6:
        score -= DEDUCT_POSE_SEVERE
        reasons.append("姿势严重不协调")
    elif pose_bad > 0.4:
        score -= DEDUCT_POSE_BAD
        reasons.append("姿势不协调")
    elif pose_bad > 0.25:
        score -= DEDUCT_POSE_SLIGHT
        reasons.append("姿势略显不自然")

    if m["pose_angle"] > 25:
        score -= DEDUCT_HEAD_TILT_SEVERE
        reasons.append("头部严重歪斜")
    elif m["pose_angle"] > 15:
        score -= DEDUCT_HEAD_TILT_SLIGHT
        reasons.append("头部轻微歪斜")

    expr_bad = _expression_quality(m["face_meshes"])
    asym = _asymmetry_score(m["face_meshes"])
    if expr_bad > 0.6:
        score -= DEDUCT_EXPR_SEVERE
        reasons.append("表情管理严重不当")
    elif expr_bad > 0.4:
        score -= DEDUCT_EXPR_BAD
        reasons.append("表情不佳")
    elif expr_bad > 0.2:
        score -= DEDUCT_EXPR_SLIGHT
        reasons.append("表情略显不自然")
    if asym > 0.5:
        score -= DEDUCT_ASYMMETRY
        reasons.append("面部表情不对称")

    face_rel = _face_relative_size(m["face_boxes"], m["img"].shape)
    if face_rel < 0.05:
        score -= DEDUCT_FACE_TINY
        reasons.append("人物太小，几乎看不清")
    elif face_rel < 0.10:
        score -= DEDUCT_FACE_SMALL
        reasons.append("人物偏小")
    elif face_rel > 0.45:
        score -= DEDUCT_FACE_BIG
        reasons.append("大头照，构图不佳")

    if m["face_boxes"]:
        biggest = max(m["face_boxes"], key=lambda b: (b[2]-b[0])*(b[3]-b[1]))
        occ = _occlusion_score(m["gray"], biggest)
        if occ > 0.5:
            score -= DEDUCT_OCCLUSION_SEVERE
            reasons.append("人物被物体严重遮挡")
        elif occ > 0.35:
            score -= DEDUCT_OCCLUSION_MODERATE
            reasons.append("人物被部分遮挡")
        elif occ > 0.2:
            score -= DEDUCT_OCCLUSION_SLIGHT
            reasons.append("人物可能被遮挡")

    colorf = colorfulness_bgr(m["img"])
    if colorf < 8 and not is_atmo:
        score -= DEDUCT_COLOR_FLAT
        reasons.append("色彩平淡")
    if contrast_q < 0.3:
        score -= DEDUCT_NO_DIMENSION
        reasons.append("人像缺乏立体感")

    return score, reasons


def _score_landscape(m, thresh, base_score, base_reasons, is_atmo, contrast_q):
    """风景类别评分。返回 (score, reasons)。"""
    score = base_score
    reasons = list(base_reasons)
    gray = m["gray"]

    if m["skew"] > thresh["landscape_skew"]:
        score -= DEDUCT_SKEW_LANDSCAPE
        reasons.append("地平线/画面歪斜")

    colorf = colorfulness_bgr(m["img"])
    if colorf < 12:
        if is_atmo:
            score -= DEDUCT_COLOR_FLAT_ATMO
            reasons.append("氛围感低饱和")
        else:
            score -= DEDUCT_COLOR_FLAT_LANDSCAPE
            reasons.append("色彩偏平淡")

    edge_density = round(float(np.mean(cv2.Canny(gray, 80, 180) > 0)), 4)
    if edge_density < 0.03:
        score -= DEDUCT_EMPTY_SCENE
        reasons.append("画面缺少重点，内容空洞")
    if m["blur"] < 120:
        if is_atmo:
            score -= DEDUCT_SOFT_ATMO
            reasons.append("氛围感柔和")
        else:
            score -= DEDUCT_SOFT_LANDSCAPE
            reasons.append("景色不够锐利")
    if contrast_q < 0.4:
        score -= DEDUCT_NO_LAYERS
        reasons.append("画面缺乏层次感")

    return score, reasons


def _score_screenshot(m, base_score, base_reasons):
    """截图类别评分。返回 (score, reasons)。"""
    score = base_score
    reasons = list(base_reasons)

    if m["blur"] < 100:
        score -= DEDUCT_SCREENSHOT_BLUR
        reasons.append("截图模糊")
    if m["ocr_conf"] > 0 and m["ocr_conf"] < 0.5:
        score -= DEDUCT_SCREENSHOT_OCR
        reasons.append("文字识别度低")

    return score, reasons


def _score_text(m, thresh, base_score, base_reasons):
    """文字类别评分。返回 (score, reasons)。"""
    score = base_score
    reasons = list(base_reasons)
    gray = m["gray"]

    if m["ocr_conf"] > 0 and m["ocr_conf"] < 0.55:
        score -= DEDUCT_TEXT_OCR_LOW
        reasons.append("文字识别置信度偏低")
    if m["skew"] > thresh["text_skew"]:
        score -= DEDUCT_TEXT_SKEW
        reasons.append("文字歪斜")
    if reflection_score(gray) > 0.08:
        score -= DEDUCT_TEXT_REFLECTION
        reasons.append("疑似反光")
    if m["blur"] < 120:
        score -= DEDUCT_TEXT_BLUR
        reasons.append("文字模糊")
    border = np.concatenate([gray[:8, :].ravel(), gray[-8:, :].ravel(), gray[:, :8].ravel(), gray[:, -8:].ravel()])
    if np.mean(border) < m["mean"] * 0.65:
        score -= DEDUCT_TEXT_BORDER
        reasons.append("边缘可能残缺")

    return score, reasons


def analyze_image_file(path: str) -> MediaResult:
    try:
        img, gray = _load_and_preprocess(path)
    except Exception as e:
        return MediaResult(path=path, media_type="image", category="unknown", score=0.0, verdict="junk", reason=str(e))

    thresh = _read_thresholds()
    m = _compute_metrics(img, gray)
    m["img"] = img
    m["gray"] = gray

    categories = infer_category(gray, m["face_count"], m["ocr_conf"], m["text_blocks"], img)
    is_atmo = _is_atmospheric(img, gray, m["mean"]) and any(c in ("portrait", "landscape") for c in categories)

    base_score, base_reasons, contrast_q, clarity = _score_global(m, thresh, is_atmo)

    best_score = base_score
    best_reasons = base_reasons

    for cat in categories:
        if cat == "portrait":
            cat_score, cat_reasons = _score_portrait(m, thresh, base_score, base_reasons, is_atmo, contrast_q)
        elif cat == "landscape":
            cat_score, cat_reasons = _score_landscape(m, thresh, base_score, base_reasons, is_atmo, contrast_q)
        elif cat == "screenshot":
            cat_score, cat_reasons = _score_screenshot(m, base_score, base_reasons)
        elif cat == "text":
            cat_score, cat_reasons = _score_text(m, thresh, base_score, base_reasons)
        else:
            continue

        if cat_score > best_score:
            best_score = cat_score
            best_reasons = cat_reasons

    seen = set()
    dedup_reasons = []
    for r in best_reasons:
        if r not in seen:
            seen.add(r)
            dedup_reasons.append(r)

    verdict = "keep" if best_score >= thresh["keep_score"] else "junk"
    reason = "；".join(dedup_reasons) if dedup_reasons else "质量正常"
    if is_atmo and "氛围" not in reason:
        reason += "；检测到氛围感风格"

    return MediaResult(
        path=path,
        media_type="image",
        category=",".join(categories),
        score=max(0.0, min(100.0, best_score)),
        verdict=verdict,
        reason=reason,
        blur=m["blur"],
        exposure=m["mean"],
        skew=m["skew"],
        face_count=m["face_count"],
        ocr_conf=m["ocr_conf"],
        face_embedding=m["face_emb"],
    )


def analyze_media(path: str) -> MediaResult:
    try:
        if is_image(path):
            return analyze_image_file(path)
        if path.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
            return analyze_video_file(path)
        return MediaResult(path=path, media_type="unknown", category="unknown", score=0.0, verdict="junk", reason="不支持的文件类型")
    except Exception as e:
        return MediaResult(
            path=path, media_type="unknown", category="unknown",
            score=0.0, verdict="junk", reason=f"分析出错: {str(e)[:50]}"
        )
