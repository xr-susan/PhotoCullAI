"""人脸特征提取与聚类，用于按人物分组照片。
同时提供共享的 insightface 实例，避免重复加载模型。"""

import logging
import os
import shutil
import zipfile

import numpy as np

from app.core.union_find import UnionFind

logger = logging.getLogger(__name__)

try:
    from insightface.app import FaceAnalysis
    try:
        import insightface.utils.storage as insightface_storage

        insightface_storage.BASE_REPO_URL = (
            "https://ghproxy.net/github.com/deepinsight/insightface/releases/download/v0.7"
        )
    except Exception:
        logger.debug("insightface 存储 URL 设置失败", exc_info=True)
except Exception:
    FaceAnalysis = None
    logger.debug("insightface 不可用，人脸特征提取功能禁用", exc_info=True)

PERSON_NAMES = [
    "人物一", "人物二", "人物三", "人物四", "人物五",
    "人物六", "人物七", "人物八", "人物九", "人物十",
    "人物十一", "人物十二", "人物十三", "人物十四", "人物十五",
    "人物十六", "人物十七", "人物十八", "人物十九", "人物二十",
]


def ensure_buffalo_l_cache():
    root = os.path.expanduser("~/.insightface")
    model_dir = os.path.join(root, "models", "buffalo_l")
    zip_path = os.path.join(root, "models", "buffalo_l.zip")

    if os.path.exists(model_dir) and os.listdir(model_dir):
        return

    if not os.path.exists(zip_path):
        return

    try:
        if os.path.exists(model_dir):
            shutil.rmtree(model_dir)
        os.makedirs(model_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(model_dir)
    except Exception:
        return


# ---- 共享 insightface 实例（避免重复加载 ~300MB 模型） ----
_shared_app = None


def get_shared_face_app():
    """返回全局唯一的 insightface FaceAnalysis 实例。"""
    global _shared_app
    if _shared_app is not None:
        return _shared_app
    if FaceAnalysis is None:
        return None
    try:
        ensure_buffalo_l_cache()
        _shared_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        _shared_app.prepare(ctx_id=-1, det_size=(640, 640))
        return _shared_app
    except Exception:
        logger.warning("insightface 共享实例初始化失败", exc_info=True)
        _shared_app = None
        return None


class FaceRecognitionService:
    """人脸特征提取服务，使用共享 insightface 实例。"""

    @property
    def available(self):
        return get_shared_face_app() is not None

    def extract_embedding(self, img_bgr):
        """提取图片中最大人脸的 512 维特征向量，无脸返回 None。"""
        app = get_shared_face_app()
        if app is None or img_bgr is None:
            return None
        try:
            import cv2
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            faces = app.get(rgb)
            if not faces:
                return None
            best = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            emb = best.normed_embedding
            if emb is None:
                return None
            return emb.astype(np.float32)
        except Exception:
            logger.debug("人脸特征提取失败", exc_info=True)
            return None


def cosine_similarity(a, b):
    """计算两个向量的余弦相似度。"""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm < 1e-8:
        return 0.0
    return float(dot / norm)


def cluster_faces(face_data, threshold=0.45):
    """
    对所有人脸特征进行聚类（并查集，传递性分组）。

    参数:
        face_data: list of (path, embedding) — 有 embedding 的图片
        threshold: 余弦相似度阈值，>= 此值认为是同一人

    返回:
        dict: path -> person_index (0-based)
    """
    if not face_data:
        return {}

    paths = [p for p, _ in face_data]
    embeddings = [e for _, e in face_data]
    n = len(embeddings)

    uf = UnionFind(n)

    # 两两比较，相似则合并
    for i in range(n):
        for j in range(i + 1, n):
            if cosine_similarity(embeddings[i], embeddings[j]) >= threshold:
                uf.union(i, j)

    # 按组分配标签
    group_map = {}
    label = 0
    result = {}
    for i in range(n):
        root = uf.find(i)
        if root not in group_map:
            group_map[root] = label
            label += 1
        result[paths[i]] = group_map[root]

    return result


def get_person_name(index):
    """根据索引返回人物名称。"""
    if 0 <= index < len(PERSON_NAMES):
        return PERSON_NAMES[index]
    return f"人物{index + 1}"
