from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class MediaResult:
    path: str
    media_type: str              # image / video / live_photo / unknown
    category: str                # portrait / landscape / text / unknown
    score: float
    verdict: str                 # keep / review / junk
    reason: str
    blur: float = 0.0
    exposure: float = 0.0
    skew: float = 0.0
    face_count: int = 0
    ocr_conf: float = 0.0
    duplicate_group: int = -1
    duplicate_keep: bool = False
    paired_video: Optional[str] = None
    paired_image: Optional[str] = None
    face_embedding: Optional[object] = None   # numpy ndarray or None
    person_label: str = ""                     # 人物一 / 人物二 / ...

    def to_dict(self):
        d = asdict(self)
        d.pop("face_embedding", None)
        return d
