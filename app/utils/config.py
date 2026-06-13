"""配置加载器 — 读取 config.yaml，提供全局 get() 访问。"""

from pathlib import Path
import yaml

_DEFAULTS = {
    "app": {
        "window_title": "PhotoCullAI",
    },
    "thresholds": {
        "keep_score": 65,
        "blur_low": 80,
        "blur_medium": 150,
        "portrait_eye_closed": 0.18,
        "landscape_skew_deg": 3.5,
        "text_skew_deg": 2.0,
        "duplicate_hamming": 10,
        "overexposure": 0.18,
        "underexposure": 0.20,
    },
    "paths": {
        "cache_dir": "data/cache",
        "reports_dir": "data/reports",
        "junk_dir": "data/junk",
    },
    "scan": {
        "image_extensions": [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".heic"],
        "video_extensions": [".mp4", ".mov", ".mkv", ".avi", ".webm"],
        "max_workers": 2,
    },
}

_config = None


def _find_config_path() -> Path:
    """按优先级查找 config.yaml"""
    candidates = [
        Path("config.yaml"),
        Path(__file__).resolve().parents[2] / "config.yaml",
        Path.home() / "config.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _load_config() -> dict:
    global _config
    if _config is not None:
        return _config

    path = _find_config_path()
    cfg = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception:
            cfg = {}

    # 深度合并默认值
    _config = _deep_merge(_DEFAULTS, cfg)
    return _config


def _deep_merge(defaults: dict, overrides: dict) -> dict:
    result = {}
    for key, val in defaults.items():
        if key in overrides and isinstance(val, dict) and isinstance(overrides[key], dict):
            result[key] = _deep_merge(val, overrides[key])
        elif key in overrides:
            result[key] = overrides[key]
        else:
            result[key] = val
    return result


def get(section: str, key: str, default=None):
    """获取配置值，用法：get("thresholds", "keep_score", 78)"""
    cfg = _load_config()
    sec = cfg.get(section, {})
    if isinstance(sec, dict):
        return sec.get(key, default)
    return default


def get_section(section: str) -> dict:
    """获取整个配置段"""
    cfg = _load_config()
    return cfg.get(section, {})
