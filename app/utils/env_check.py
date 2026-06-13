import importlib

CRITICAL_DEPENDENCIES = (
    "PyQt6",
    "cv2",
    "numpy",
    "PIL",
    "pillow_heif",
)

OPTIONAL_DEPENDENCIES = (
    "paddle",
    "paddleocr",
    "onnxruntime",
    "imagehash",
    "yaml",
)


def get_missing_dependencies() -> list[str]:
    missing = []
    for package in CRITICAL_DEPENDENCIES:
        try:
            importlib.import_module(package)
        except Exception:
            missing.append(package)
    return missing


def get_optional_missing_dependencies() -> list[str]:
    missing = []
    for package in OPTIONAL_DEPENDENCIES:
        try:
            importlib.import_module(package)
        except Exception:
            missing.append(package)
    return missing


def format_install_command() -> str:
    return "python -m pip install -r requirements.txt"
