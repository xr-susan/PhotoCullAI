from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".heic"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTS


def is_video(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTS


def is_supported_media_path(path: str) -> bool:
    return is_image(path) or is_video(path)


def normalize_input_paths(paths):
    normalized = []
    seen = set()

    for raw_path in paths or []:
        if raw_path is None:
            continue

        path = Path(str(raw_path)).expanduser()
        try:
            resolved = path.resolve(strict=False)
        except Exception:
            resolved = path

        if not resolved.exists():
            continue

        key = str(resolved)
        if key in seen:
            continue

        seen.add(key)
        normalized.append(key)

    return normalized


def list_media_files(root: str):
    root_path = Path(root)
    # 排除的目录
    exclude_dirs = {'.venv', 'venv', '__pycache__', '.git', 'node_modules', '.idea', '.vscode'}

    for p in root_path.rglob("*"):
        # 检查是否在排除的目录中
        if any(part in exclude_dirs for part in p.parts):
            continue
        if p.is_file() and (is_image(str(p)) or is_video(str(p))):
            yield str(p)
