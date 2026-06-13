import logging
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    logger.debug("pillow_heif 注册失败，HEIC 格式可能不可用", exc_info=True)


def safe_imread(path: str):
    arr = np.fromfile(path, dtype=np.uint8)
    if arr.size == 0:
        return None
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def resize_long_side(img, max_side=1600):
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1:
        return img
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def bgr_to_gray(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def blur_score(gray):
    """计算模糊度（Laplacian 方差），越高越清晰。"""
    try:
        return round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2)
    except Exception:
        return 0.0


def brightness_metrics(gray):
    """计算亮度指标：(均值, 过曝比例, 欠曝比例)。"""
    try:
        mean = round(float(np.mean(gray)), 2)
        over = round(float(np.mean(gray >= 245)), 4)
        under = round(float(np.mean(gray <= 10)), 4)
        return mean, over, under
    except Exception:
        return 0.0, 0.0, 0.0


def load_qpixmap(path: str, max_side: int = 1200):
    from PyQt6.QtGui import QImage, QPixmap

    try:
        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((max_side, max_side))

        width, height = img.size
        raw = img.tobytes("raw", "RGB")
        qimg = QImage(raw, width, height, width * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        if not pixmap.isNull():
            return pixmap
    except Exception:
        logger.debug("PIL 加载图片失败，回退 QPixmap: %s", path, exc_info=True)

    try:
        return QPixmap(path)
    except Exception:
        return QPixmap()
