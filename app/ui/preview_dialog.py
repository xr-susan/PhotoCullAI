from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame,
    QPushButton, QWidget
)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QImage, QPixmap, QTransform, QPainter

from app.utils.image_utils import load_qpixmap


class PannableImageWidget(QWidget):
    """支持缩放和拖动平移的图片控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._dragging = False
        self._drag_start = QPoint(0, 0)
        self._min_scale = 0.05
        self._max_scale = 8.0
        self.setMinimumSize(200, 200)

    def set_pixmap(self, pix):
        self._pixmap = pix
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._fit_view()
        self.update()

    def _fit_view(self):
        if self._pixmap is None or self._pixmap.isNull():
            return
        pw, ph = self.width(), self.height()
        iw, ih = self._pixmap.width(), self._pixmap.height()
        if iw == 0 or ih == 0:
            return
        self._scale = min(pw / iw, ph / ih, 1.0)
        sw = int(iw * self._scale)
        sh = int(ih * self._scale)
        self._offset = QPoint((pw - sw) // 2, (ph - sh) // 2)
        self.update()

    def _scaled_size(self):
        if self._pixmap is None:
            return 0, 0
        return int(self._pixmap.width() * self._scale), int(self._pixmap.height() * self._scale)

    def paintEvent(self, event):
        if self._pixmap is None or self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        sw, sh = self._scaled_size()
        if sw < 1 or sh < 1:
            painter.end()
            return
        scaled = self._pixmap.scaled(sw, sh, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(self._offset.x(), self._offset.y(), scaled)
        painter.end()

    def zoom_in(self):
        self._zoom_at(self.width() // 2, self.height() // 2, 1.25)

    def zoom_out(self):
        self._zoom_at(self.width() // 2, self.height() // 2, 1.0 / 1.25)

    def zoom_fit(self):
        self._fit_view()

    def zoom_original(self):
        if self._pixmap is None:
            return
        pw, ph = self.width(), self.height()
        iw, ih = self._pixmap.width(), self._pixmap.height()
        self._scale = 1.0
        self._offset = QPoint((pw - iw) // 2, (ph - ih) // 2)
        self.update()

    def _zoom_at(self, cx, cy, factor):
        new_scale = max(self._min_scale, min(self._max_scale, self._scale * factor))
        if new_scale == self._scale:
            return
        # 计算鼠标位置在图片上的对应点
        ix = (cx - self._offset.x()) / self._scale
        iy = (cy - self._offset.y()) / self._scale
        self._scale = new_scale
        # 调整偏移使鼠标位置不变
        self._offset = QPoint(int(cx - ix * self._scale), int(cy - iy * self._scale))
        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        pos = event.position()
        cx, cy = int(pos.x()), int(pos.y())
        if delta > 0:
            self._zoom_at(cx, cy, 1.15)
        elif delta < 0:
            self._zoom_at(cx, cy, 1.0 / 1.15)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = event.pos()

    def mouseMoveEvent(self, event):
        if self._dragging:
            dx = event.pos().x() - self._drag_start.x()
            dy = event.pos().y() - self._drag_start.y()
            self._offset += QPoint(dx, dy)
            self._drag_start = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def get_scale_percent(self):
        return int(self._scale * 100)


class PreviewDialog(QDialog):
    def __init__(self, result, all_results=None, parent=None):
        super().__init__(parent)
        self.result = result
        self.all_results = all_results or [result]
        self.current_index = self.all_results.index(result) if result in self.all_results else 0
        self._current_rotation = 0
        self._base_pixmap = None

        self.setWindowTitle("照片预览")
        self.resize(1200, 850)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # 顶部导航栏
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)

        self.btn_prev = QPushButton("上一张")
        self.btn_prev.setFixedWidth(80)
        self.btn_prev.clicked.connect(self._go_prev)

        self.nav_info = QLabel()
        self.nav_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nav_info.setStyleSheet("color: #5B8C9E; font-size: 14px;")

        self.btn_next = QPushButton("下一张")
        self.btn_next.setFixedWidth(80)
        self.btn_next.clicked.connect(self._go_next)

        nav_bar.addStretch()
        nav_bar.addWidget(self.btn_prev)
        nav_bar.addWidget(self.nav_info)
        nav_bar.addWidget(self.btn_next)
        nav_bar.addStretch()
        main_layout.addLayout(nav_bar)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        btn_zoom_out = QPushButton("缩小")
        btn_zoom_out.clicked.connect(self._on_zoom_out)

        btn_zoom_fit = QPushButton("适应窗口")
        btn_zoom_fit.clicked.connect(self._on_zoom_fit)

        btn_zoom_in = QPushButton("放大")
        btn_zoom_in.clicked.connect(self._on_zoom_in)

        btn_zoom_orig = QPushButton("原始大小")
        btn_zoom_orig.clicked.connect(self._on_zoom_orig)

        btn_rotate_ccw = QPushButton("左旋90")
        btn_rotate_ccw.clicked.connect(lambda: self._rotate_image(-90))

        btn_rotate_cw = QPushButton("右旋90")
        btn_rotate_cw.clicked.connect(lambda: self._rotate_image(90))

        for btn in [btn_zoom_out, btn_zoom_fit, btn_zoom_in, btn_zoom_orig,
                    btn_rotate_ccw, btn_rotate_cw]:
            btn.setFixedHeight(32)
            toolbar.addWidget(btn)

        toolbar.addStretch()

        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #5B8C9E; font-size: 12px; min-width: 60px;")
        toolbar.addWidget(self.zoom_label)

        main_layout.addLayout(toolbar)

        # 图片区域
        self.image_widget = PannableImageWidget()
        self.image_widget.setStyleSheet("background: rgba(0,0,0,0.03); border-radius: 10px;")
        main_layout.addWidget(self.image_widget, stretch=1)

        # 信息面板
        info_frame = QFrame()
        info_frame.setObjectName("previewInfo")
        self.info_layout = QGridLayout(info_frame)
        self.info_layout.setContentsMargins(12, 8, 12, 8)
        self.info_layout.setHorizontalSpacing(16)
        self.info_layout.setVerticalSpacing(6)
        main_layout.addWidget(info_frame)

        self._load_current()

    def _on_zoom_in(self):
        self.image_widget.zoom_in()
        self.zoom_label.setText(f"{self.image_widget.get_scale_percent()}%")

    def _on_zoom_out(self):
        self.image_widget.zoom_out()
        self.zoom_label.setText(f"{self.image_widget.get_scale_percent()}%")

    def _on_zoom_fit(self):
        self.image_widget.zoom_fit()
        self.zoom_label.setText(f"{self.image_widget.get_scale_percent()}%")

    def _on_zoom_orig(self):
        self.image_widget.zoom_original()
        self.zoom_label.setText(f"{self.image_widget.get_scale_percent()}%")

    def _go_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.result = self.all_results[self.current_index]
            self._current_rotation = 0
            self._load_current()

    def _go_next(self):
        if self.current_index < len(self.all_results) - 1:
            self.current_index += 1
            self.result = self.all_results[self.current_index]
            self._current_rotation = 0
            self._load_current()

    def _load_current(self):
        self.nav_info.setText(f"{self.current_index + 1} / {len(self.all_results)}")
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < len(self.all_results) - 1)

        source = self.result.paired_image or self.result.path
        pix = load_qpixmap(source, 2400)
        if not pix.isNull():
            self._base_pixmap = pix
            self._current_rotation = 0
            self.image_widget.set_pixmap(pix)
            self.zoom_label.setText(f"{self.image_widget.get_scale_percent()}%")
        else:
            self._base_pixmap = None
            self.image_widget.set_pixmap(QPixmap())

        self._build_info()

    def _rotate_image(self, degrees):
        if self._base_pixmap is None or self._base_pixmap.isNull():
            return
        self._current_rotation = (self._current_rotation + degrees) % 360
        transform = QTransform().rotate(degrees)
        rotated = self._base_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self._base_pixmap = rotated
        self.image_widget.set_pixmap(rotated)
        self.zoom_label.setText(f"{self.image_widget.get_scale_percent()}%")

    def _build_info(self):
        while self.info_layout.count():
            item = self.info_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        r = self.result

        verdict_colors = {
            "keep": ("#27AE60", "保留"),
            "review": ("#D4A017", "待审核"),
            "junk": ("#E74C3C", "废片"),
        }
        verdict_color, verdict_text = verdict_colors.get(r.verdict, ("#888", r.verdict))

        media_type_map = {"image": "图片", "video": "视频", "live_photo": "实况照片", "unknown": "未知"}
        category_map = {"portrait": "人像", "landscape": "风景", "text": "文字", "screenshot": "截图", "video": "视频", "unknown": "未知"}
        cats = r.category.split(",") if "," in r.category else [r.category]
        cat_display = "·".join(category_map.get(c.strip(), c.strip()) for c in cats)

        fields = [
            ("文件路径", r.path),
            ("类型", media_type_map.get(r.media_type, r.media_type)),
            ("分类", cat_display),
            ("评分", f"{r.score:.1f} 分"),
            ("建议", verdict_text),
            ("原因", r.reason),
        ]

        if r.face_count > 0:
            fields.append(("人脸数", str(r.face_count)))
        if r.ocr_conf > 0:
            fields.append(("OCR 置信度", f"{r.ocr_conf:.2f}"))
        if r.blur > 0:
            fields.append(("模糊度", f"{r.blur:.1f}"))
        if r.exposure > 0:
            fields.append(("曝光均值", f"{r.exposure:.1f}"))
        if r.skew > 0:
            fields.append(("歪斜角度", f"{r.skew:.1f} 度"))
        if r.paired_video:
            fields.append(("配对视频", r.paired_video))

        row = 0
        for label_text, value in fields:
            lbl = QLabel(label_text)
            lbl.setObjectName("previewTitle")
            lbl.setFixedWidth(90)
            self.info_layout.addWidget(lbl, row, 0)

            val = QLabel(str(value))
            val.setObjectName("previewValue")
            val.setWordWrap(True)

            if label_text == "建议":
                val.setStyleSheet(f"color: {verdict_color}; font-weight: bold; font-size: 15px;")

            self.info_layout.addWidget(val, row, 1)
            row += 1

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self._go_prev()
        elif event.key() == Qt.Key.Key_Right:
            self._go_next()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            self._on_zoom_in()
        elif event.key() == Qt.Key.Key_Minus:
            self._on_zoom_out()
        elif event.key() == Qt.Key.Key_0:
            self._on_zoom_fit()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口大小改变时重新适应
        if self._base_pixmap and not self._base_pixmap.isNull():
            self.image_widget._fit_view()
            self.zoom_label.setText(f"{self.image_widget.get_scale_percent()}%")
