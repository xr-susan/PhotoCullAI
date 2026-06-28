import cv2
import numpy as np
from app.core.types import MediaResult
from app.utils.image_utils import resize_long_side, blur_score, brightness_metrics
from app.utils.config import get


def _sample_frames(video_path, every_n_frames=30, max_frames=12):
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        frames = []
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % every_n_frames == 0:
                if frame is not None and frame.size > 0:
                    frames.append(frame)
                if len(frames) >= max_frames:
                    break
            idx += 1
        return frames
    except Exception:
        return []
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def analyze_video_file(video_path: str) -> MediaResult:
    try:
        frames = _sample_frames(video_path)
        if not frames:
            return MediaResult(
                path=video_path,
                media_type="video",
                category="unknown",
                score=50.0,
                verdict="junk",
                reason="无法读取视频或无关键帧",
            )

        blur_vals, means, overs, unders = [], [], [], []
        for f in frames:
            try:
                f = resize_long_side(f, 1280)
                gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
                b = blur_score(gray)
                m, o, u = brightness_metrics(gray)
                blur_vals.append(b)
                means.append(m)
                overs.append(o)
                unders.append(u)
            except Exception:
                continue

        if not blur_vals:
            return MediaResult(
                path=video_path,
                media_type="video",
                category="unknown",
                score=50.0,
                verdict="junk",
                reason="视频帧处理失败",
            )

        avg_blur = float(np.mean(blur_vals))
        mean_exp = float(np.mean(means))
        over = float(np.mean(overs))
        under = float(np.mean(unders))

        keep_score = get("thresholds", "keep_score", 78)
        blur_low = get("thresholds", "blur_low", 80)
        blur_medium = get("thresholds", "blur_medium", 150)
        over_thresh = get("thresholds", "overexposure", 0.18)
        under_thresh = get("thresholds", "underexposure", 0.20)

        score = 100.0
        reasons = []

        if avg_blur < blur_low:
            score -= 35
            reasons.append("视频整体模糊")
        elif avg_blur < blur_medium:
            score -= 15
            reasons.append("视频轻微模糊")

        if over > over_thresh:
            score -= 15
            reasons.append("过曝")
        if under > under_thresh:
            score -= 12
            reasons.append("欠曝")

        if len(frames) < 3:
            score -= 20
            reasons.append("视频太短/关键帧过少")

        verdict = "keep" if score >= keep_score else "junk"

        return MediaResult(
            path=video_path,
            media_type="video",
            category="video",
            score=max(0.0, min(100.0, score)),
            verdict=verdict,
            reason="；".join(reasons) if reasons else "质量正常",
            blur=avg_blur,
            exposure=mean_exp,
        )
    except Exception as e:
        return MediaResult(
            path=video_path,
            media_type="video",
            category="unknown",
            score=0.0,
            verdict="junk",
            reason=f"视频分析出错: {str(e)[:50]}",
        )
