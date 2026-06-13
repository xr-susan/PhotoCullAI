import logging
from pathlib import Path

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QCheckBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from app.utils.image_utils import load_qpixmap

logger = logging.getLogger(__name__)


class _ThumbLoaderThread(QThread):
    loaded = pyqtSignal(str, QPixmap)

    def __init__(self, tasks, parent=None):
        super().__init__(parent)
        self._tasks = tasks

    def run(self):
        for path, max_side in self._tasks:
            try:
                pix = load_qpixmap(path, max_side)
                self.loaded.emit(path, pix)
            except Exception:
                logger.exception("缩略图加载异常: %s", path)


class _ThumbManager:
    """缩略图加载队列管理器（类级别单例）。"""

    def __init__(self):
        self.queue = []
        self.loader = None
        self.callbacks = {}

    def enqueue(self, path, max_side, callback):
        self.callbacks.setdefault(path, []).append(callback)
        self.queue.append((path, max_side))
        if self.loader is None or not self.loader.isRunning():
            self._flush()

    def _flush(self):
        if not self.queue:
            return
        tasks = self.queue[:20]
        self.queue = self.queue[20:]
        self.loader = _ThumbLoaderThread(tasks)
        self.loader.loaded.connect(self._on_loaded)
        self.loader.finished.connect(self._on_batch_done)
        self.loader.start()

    def _on_loaded(self, path, pix):
        for cb in self.callbacks.pop(path, []):
            try:
                cb(pix)
            except RuntimeError:
                logger.debug("缩略图回调时 widget 已销毁: %s", path)
            except Exception:
                logger.exception("缩略图回调异常: %s", path)

    def _on_batch_done(self):
        if self.queue:
            self._flush()


_thumb_manager = _ThumbManager()


class ThumbnailCard(QFrame):
    def __init__(self, result, on_open=None, parent=None):
        super().__init__(parent)
        self.result = result
        self.on_open = on_open

        self.setFixedSize(220, 310)
        self.setObjectName("thumbCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        self.checkbox = QCheckBox("选择")
        top.addWidget(self.checkbox)
        top.addStretch()
        layout.addLayout(top)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedHeight(170)
        self.image_label.setText("加载中...")
        self.image_label.setStyleSheet("color: #8BA8B8; font-size: 11px;")
        layout.addWidget(self.image_label)

        source = result.paired_image or result.path
        _thumb_manager.enqueue(source, 400, self._on_loaded)

        filename = Path(result.paired_image or result.path).name
        self.filename_label = QLabel(filename)
        self.filename_label.setWordWrap(True)
        self.filename_label.setStyleSheet("font-size: 12px; color: #34495E; font-weight: bold;")
        self.filename_label.setMaximumHeight(36)
        layout.addWidget(self.filename_label)

        category_map = {
            "portrait": "人像",
            "landscape": "风景",
            "text": "文字",
            "screenshot": "截图",
            "video": "视频",
            "unknown": "未知",
        }
        cats = result.category.split(",") if "," in result.category else [result.category]
        cat_text = "·".join(category_map.get(c.strip(), c.strip()) for c in cats)

        media_icon = ""
        if result.media_type == "video":
            media_icon = " "
        elif result.media_type == "live_photo":
            media_icon = " "

        self.meta_label = QLabel(f"{media_icon}{cat_text}  |  {result.score:.0f} 分")
        self.meta_label.setStyleSheet("color: #5B8C9E; font-size: 12px;")
        layout.addWidget(self.meta_label)

        if result.person_label:
            person_badge = QLabel(f" {result.person_label}")
            person_badge.setStyleSheet(
                "background: rgba(135,206,235,0.2); color: #1A5276; "
                "padding: 2px 8px; border-radius: 8px; font-size: 11px; font-weight: bold;"
            )
            layout.addWidget(person_badge)

        bottom = QHBoxLayout()
        verdict_map = {"keep": "保留", "junk": "废片"}
        verdict_text = verdict_map.get(result.verdict, result.verdict)
        self.score_label = QLabel(verdict_text)

        verdict_style = {
            "keep": "background: rgba(46,204,113,0.2); color: #27AE60; padding: 4px 12px; border-radius: 10px; font-weight: bold; font-size: 12px;",
            "junk": "background: rgba(231,76,60,0.2); color: #E74C3C; padding: 4px 12px; border-radius: 10px; font-weight: bold; font-size: 12px;",
        }.get(result.verdict, "")
        self.score_label.setStyleSheet(verdict_style)

        bottom.addWidget(self.score_label)
        bottom.addStretch()

        if result.duplicate_group >= 0:
            if result.duplicate_keep:
                dup_badge = QLabel("最佳 · 建议保留")
                dup_badge.setStyleSheet(
                    "background: rgba(46,204,113,0.25); color: #27AE60; "
                    "padding: 2px 8px; border-radius: 8px; font-size: 11px; font-weight: bold;"
                )
            else:
                dup_badge = QLabel("相似 · 建议删除")
                dup_badge.setStyleSheet(
                    "background: rgba(231,76,60,0.15); color: #E74C3C; "
                    "padding: 2px 8px; border-radius: 8px; font-size: 11px; font-weight: bold;"
                )
            bottom.addWidget(dup_badge)

        layout.addLayout(bottom)

    def _on_loaded(self, pix):
        if self.image_label is None:
            return
        if pix.isNull():
            self.image_label.setText("无预览")
            self.image_label.setStyleSheet("color: #8BA8B8; font-size: 12px;")
        else:
            scaled = pix.scaled(200, 170, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.setStyleSheet("background: rgba(135, 206, 235, 0.1); border-radius: 8px;")

    def mouseDoubleClickEvent(self, event):
        if self.on_open:
            self.on_open(self.result)
