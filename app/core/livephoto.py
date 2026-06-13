from pathlib import Path
from app.core.types import MediaResult
from app.core.analyzer import analyze_image_file
from app.core.video_analyzer import analyze_video_file
from app.utils.config import get


def detect_live_pair(folder_or_file: str):
    path = Path(folder_or_file)
    root = path if path.is_dir() else path.parent

    heic_map = {}
    mov_map = {}

    try:
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            stem = p.stem.lower()
            if ext in {".heic", ".jpg", ".jpeg", ".png"}:
                heic_map[stem] = str(p)
            elif ext == ".mov":
                mov_map[stem] = str(p)
    except Exception:
        pass

    pairs = []
    for stem, img_path in heic_map.items():
        if stem in mov_map:
            pairs.append((img_path, mov_map[stem]))
    return pairs


def analyze_live_pair(image_path: str, video_path: str) -> MediaResult:
    try:
        img_result = analyze_image_file(image_path)
        vid_result = analyze_video_file(video_path)

        keep_score = get("thresholds", "keep_score", 78)

        score = img_result.score * 0.6 + vid_result.score * 0.4
        reasons = []
        if img_result.score < 60:
            reasons.append("封面质量差")
        if vid_result.score < 60:
            reasons.append("动态部分质量差")

        verdict = "keep" if score >= keep_score else "junk"

        return MediaResult(
            path=image_path,
            media_type="live_photo",
            category=img_result.category,
            score=score,
            verdict=verdict,
            reason="；".join(reasons) if reasons else "Live Photo 质量正常",
            blur=img_result.blur,
            exposure=img_result.exposure,
            skew=img_result.skew,
            face_count=img_result.face_count,
            ocr_conf=img_result.ocr_conf,
            paired_video=video_path,
            paired_image=image_path,
        )
    except Exception as e:
        return MediaResult(
            path=image_path,
            media_type="live_photo",
            category="unknown",
            score=0.0,
            verdict="junk",
            reason=f"Live Photo 分析出错: {str(e)[:50]}",
            paired_video=video_path,
            paired_image=image_path,
        )
