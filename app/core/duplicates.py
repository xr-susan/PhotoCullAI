import logging
import os
from collections import defaultdict

try:
    import imagehash
    from PIL import Image
except Exception:
    imagehash = None
    Image = None

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

from app.utils.config import get
from app.utils.image_utils import safe_imread
from app.core.union_find import UnionFind

try:
    import pillow_heif
    if Image is not None:
        pillow_heif.register_heif_opener()
except Exception:
    pass

logger = logging.getLogger(__name__)


def _file_signature(path):
    try:
        stat = os.stat(path)
        return (stat.st_size, os.path.splitext(path)[1].lower())
    except Exception:
        return None


def _compute_hashes(path):
    """计算多种哈希：pHash + dHash + aHash，返回 dict。"""
    if imagehash is None or Image is None:
        return {}
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            return {
                "phash": imagehash.phash(img, hash_size=8),
                "dhash": imagehash.dhash(img, hash_size=8),
                "ahash": imagehash.average_hash(img, hash_size=8),
            }
    except Exception:
        return {}


def _is_visually_similar(path_a, path_b, hash_dists):
    """多哈希投票 + SSIM 验证，判断两张图是否真正相似。"""
    # 投票：至少 2 种哈希在阈值内
    vote = 0
    phash_dist = hash_dists.get("phash", 999)
    dhash_dist = hash_dists.get("dhash", 999)
    ahash_dist = hash_dists.get("ahash", 999)

    if phash_dist <= 12:
        vote += 1
    if dhash_dist <= 12:
        vote += 1
    if ahash_dist <= 12:
        vote += 1

    if vote >= 2:
        return True

    # pHash 很接近但只差一点 → 用 SSIM 验证
    if phash_dist <= 16 and cv2 is not None and np is not None:
        try:
            img_a = safe_imread(path_a)
            img_b = safe_imread(path_b)
            if img_a is not None and img_b is not None:
                # 统一尺寸
                size = (160, 120)
                a = cv2.resize(cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY), size)
                b = cv2.resize(cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY), size)
                # 简化 SSIM：用归一化互相关
                a_f = a.astype(np.float64)
                b_f = b.astype(np.float64)
                a_norm = (a_f - a_f.mean()) / (a_f.std() + 1e-6)
                b_norm = (b_f - b_f.mean()) / (b_f.std() + 1e-6)
                ssim_val = float(np.mean(a_norm * b_norm))
                if ssim_val > 0.6:
                    return True
        except Exception:
            pass

    return False


def group_duplicates(results):
    """多哈希 + SSIM 检测相似照片，支持传递性分组。"""
    # 计算所有图片的多哈希
    hash_data = {}  # index -> {"phash": ..., "dhash": ..., "ahash": ...}

    for i, r in enumerate(results):
        if r.media_type == "video":
            continue
        hashes = _compute_hashes(r.path)
        if hashes:
            hash_data[i] = hashes

    if not hash_data:
        return []

    indices = list(hash_data.keys())
    n = len(indices)
    uf = UnionFind(len(results))

    # 两两比较多哈希
    for a in range(n):
        for b in range(a + 1, n):
            ia, ib = indices[a], indices[b]
            ha, hb = hash_data[ia], hash_data[ib]

            # 计算各种哈希距离
            dists = {}
            for key in ("phash", "dhash", "ahash"):
                if key in ha and key in hb:
                    dists[key] = ha[key] - hb[key]

            if _is_visually_similar(results[ia].path, results[ib].path, dists):
                uf.union(ia, ib)

    hash_groups = uf.groups()

    # 补充：用文件大小分组（完全相同的文件）
    assigned = set()
    for g in hash_groups:
        assigned.update(g)

    size_map = defaultdict(list)
    for i, r in enumerate(results):
        if i in assigned:
            continue
        if r.media_type == "video":
            continue
        sig = _file_signature(r.path)
        if sig is None:
            continue
        size, ext = sig
        size_map[(size, ext)].append(i)

    for key, group in size_map.items():
        if len(group) > 1:
            hash_groups.append(group)

    # 补充：按 EXIF 拍摄时间分组（3 秒内连拍视为相似）
    try:
        _group_by_time(results, hash_groups, uf, assigned)
        hash_groups = uf.groups()
    except Exception:
        logger.debug("按时间分组失败", exc_info=True)

    return hash_groups


def _get_photo_time(path):
    """从 EXIF 获取拍摄时间戳。"""
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            # 36867 = DateTimeOriginal, 306 = DateTime
            for tag_id in (36867, 36868, 306):
                val = exif.get(tag_id)
                if val:
                    # 格式: "2026:01:07 17:21:19"
                    return val
    except Exception:
        pass
    return None


def _group_by_time(results, existing_groups, uf, assigned):
    """按拍摄时间分组：同一目录下 3 秒内连拍的照片归为相似组。"""
    time_entries = []  # (index, timestamp_seconds, directory)
    for i, r in enumerate(results):
        if i in assigned:
            continue
        if r.media_type == "video":
            continue
        ts = _get_photo_time(r.path)
        if ts is None:
            continue
        try:
            # 解析时间 "2026:01:07 17:21:19"
            parts = ts.replace(":", "-", 2).split(" ")
            date_part = parts[0]  # "2026-01-07"
            time_part = parts[1] if len(parts) > 1 else "00:00:00"
            h, m, s = [int(x) for x in time_part.split(":")]
            total_sec = h * 3600 + m * 60 + s
            directory = os.path.dirname(r.path)
            time_entries.append((i, total_sec, directory))
        except Exception:
            continue

    # 按目录分组，然后按时间排序
    dir_groups = defaultdict(list)
    for idx, ts, d in time_entries:
        dir_groups[d].append((idx, ts))

    for directory, entries in dir_groups.items():
        entries.sort(key=lambda x: x[1])
        for a in range(len(entries)):
            for b in range(a + 1, len(entries)):
                idx_a, ts_a = entries[a]
                idx_b, ts_b = entries[b]
                if ts_b - ts_a > 3:
                    break  # 时间差超过 3 秒，后面的更不可能
                uf.union(idx_a, idx_b)


def apply_duplicate_policy(results):
    groups = group_duplicates(results)
    for gid, group in enumerate(groups):
        keeper = max(group, key=lambda idx: results[idx].score)
        for idx in group:
            results[idx].duplicate_group = gid
            results[idx].duplicate_keep = (idx == keeper)
            if idx != keeper and results[idx].verdict == "keep":
                results[idx].verdict = "junk"
                if "相似图中非最佳" not in results[idx].reason:
                    results[idx].reason += "；相似图中非最佳"
    return groups
