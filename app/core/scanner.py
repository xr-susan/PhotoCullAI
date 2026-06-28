import logging
import threading
from pathlib import Path
from app.core.analyzer import analyze_media
from app.core.livephoto import detect_live_pair, analyze_live_pair
from app.utils.file_utils import list_media_files

logger = logging.getLogger(__name__)


def collect_media_files(inputs):
    all_media = []
    live_pairs = {}
    seen_paths = set()

    for item in inputs:
        item_path = Path(item)
        if item_path.exists() and item_path.is_dir():
            try:
                for img_path, mov_path in detect_live_pair(str(item_path)):
                    live_pairs[img_path] = mov_path
            except Exception:
                logger.debug("Live Photo 检测失败: %s", item_path, exc_info=True)

    for item in inputs:
        p = Path(item)
        if not p.exists():
            continue
        if p.is_dir():
            for media_path in list_media_files(str(p)):
                if media_path not in live_pairs and media_path not in seen_paths:
                    seen_paths.add(media_path)
                    all_media.append(media_path)
        else:
            path_str = str(p)
            if path_str not in live_pairs and path_str not in seen_paths:
                seen_paths.add(path_str)
                all_media.append(path_str)

    for img_path, mov_path in live_pairs.items():
        if img_path not in seen_paths:
            seen_paths.add(img_path)
            all_media.append(("live_pair", img_path, mov_path))

    return all_media


def analyze_one(item, cancel_event: threading.Event = None):
    """分析单个文件，支持通过 cancel_event 中途取消。"""
    if cancel_event and cancel_event.is_set():
        from app.core.types import MediaResult

        name = item[1] if isinstance(item, tuple) else item
        return MediaResult(
            path=name,
            media_type="unknown",
            category="unknown",
            score=0.0,
            verdict="junk",
            reason="已取消扫描",
        )
    try:
        if isinstance(item, tuple):
            _, img_path, mov_path = item
            return analyze_live_pair(img_path, mov_path)
        else:
            return analyze_media(item)
    except Exception as e:
        logging.exception("分析文件失败：%s", item)
        from app.core.types import MediaResult

        name = item[1] if isinstance(item, tuple) else item
        return MediaResult(
            path=name,
            media_type="unknown",
            category="unknown",
            score=0.0,
            verdict="junk",
            reason=f"分析出错: {str(e)[:40]}",
        )
