import math
import random

from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QWidget


class Cloud:
    __slots__ = ('x', 'y', 'base_y', 'size', 'speed', 'base_opacity',
                 'opacity', 'wobble_offset', 'wobble_speed', 'wobble_amp',
                 'breathe_offset', 'breathe_speed', 'breathe_amp',
                 'drift_y_offset', 'drift_y_speed', 'drift_y_amp', 'seed')
    def __init__(self, x, y, size, speed, opacity):
        self.x = x
        self.y = y
        self.base_y = y
        self.size = size
        self.speed = speed
        self.base_opacity = opacity
        self.opacity = opacity
        self.wobble_offset = random.uniform(0, math.pi * 2)
        self.wobble_speed = random.uniform(0.01, 0.035)
        self.wobble_amp = random.uniform(0.6, 2.0)
        self.breathe_offset = random.uniform(0, math.pi * 2)
        self.breathe_speed = random.uniform(0.005, 0.015)
        self.breathe_amp = random.uniform(0.05, 0.15)
        self.drift_y_offset = random.uniform(0, math.pi * 2)
        self.drift_y_speed = random.uniform(0.003, 0.008)
        self.drift_y_amp = random.uniform(15, 50)
        self.seed = random.randint(0, 999)


class CloudBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.clouds = []
        self.time = 0
        self._init_clouds()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(200)  # 降低刷新频率：80ms → 200ms

    def _init_clouds(self):
        presets = [
            (-100, 60, 160, 0.45, 0.30),
            (500, 40, 140, 0.50, 0.28),
            (1100, 50, 150, 0.55, 0.30),
            (50, 250, 130, 0.25, 0.20),
            (700, 220, 145, 0.35, 0.22),
            (1300, 240, 135, 0.32, 0.21),
            (300, 500, 140, 0.22, 0.15),
            (1000, 480, 130, 0.25, 0.14),
            (100, 650, 120, 0.15, 0.12),
            (900, 620, 135, 0.16, 0.13),
            (400, 160, 110, 0.55, 0.28),
            (1200, 550, 105, 0.38, 0.18),
        ]
        for x, y, size, speed, opacity in presets:
            self.clouds.append(Cloud(x, y, size, speed, opacity))

    def showEvent(self, event):
        super().showEvent(event)
        if not self.timer.isActive():
            self.timer.start(200)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.timer.stop()

    def _tick(self):
        self.time += 1
        w = self.width()
        for c in self.clouds:
            c.x += c.speed
            # 垂直方向的正弦漂移
            c.y = c.base_y + math.sin(self.time * c.wobble_speed + c.wobble_offset) * c.wobble_amp
            # 缓慢的大范围垂直漂移
            c.y += math.sin(self.time * c.drift_y_speed + c.drift_y_offset) * c.drift_y_amp
            # 透明度呼吸效果
            breathe = math.sin(self.time * c.breathe_speed + c.breathe_offset) * c.breathe_amp
            c.opacity = max(0.05, min(0.45, c.base_opacity + breathe))
            if c.x > w + c.size * 2:
                c.x = -c.size * 2.5
            if c.x < -c.size * 3:
                c.x = w + c.size
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for c in self.clouds:
            self._draw_cloud(painter, c)

        painter.end()

    def _draw_cloud(self, painter, cloud):
        painter.save()
        painter.translate(QPointF(cloud.x, cloud.y))
        painter.setOpacity(cloud.opacity)

        s = cloud.size
        painter.setPen(Qt.PenStyle.NoPen)

        base_alpha = int(220 * min(1.0, cloud.opacity / 0.25))
        color = QColor(255, 255, 255, base_alpha)
        painter.setBrush(QBrush(color))

        self._draw_cloud_shape(painter, s, cloud.seed)

        painter.setBrush(QBrush(QColor(255, 255, 255, int(base_alpha * 0.6))))
        self._draw_cloud_highlights(painter, s, cloud.seed)

        painter.restore()

    def _draw_cloud_shape(self, painter, s, seed):
        r = random.Random(seed)

        body = QRectF(-s * 0.45, -s * 0.08, s * 0.9, s * 0.28)
        painter.drawEllipse(body)

        bumps = [
            (-s * 0.25, -s * 0.22, s * 0.35, s * 0.30),
            (s * 0.05, -s * 0.28, s * 0.30, s * 0.32),
            (-s * 0.40, -s * 0.10, s * 0.25, s * 0.24),
            (s * 0.25, -s * 0.15, s * 0.22, s * 0.25),
            (-s * 0.10, -s * 0.18, s * 0.28, s * 0.26),
        ]

        for bx, by, bw, bh in bumps:
            offset_x = r.uniform(-s * 0.03, s * 0.03)
            offset_y = r.uniform(-s * 0.03, s * 0.03)
            painter.drawEllipse(QRectF(bx + offset_x, by + offset_y, bw, bh))

    def _draw_cloud_highlights(self, painter, s, seed):
        r = random.Random(seed + 100)

        highlights = [
            (-s * 0.15, -s * 0.25, s * 0.18, s * 0.14),
            (s * 0.10, -s * 0.20, s * 0.15, s * 0.12),
            (-s * 0.30, -s * 0.08, s * 0.12, s * 0.10),
        ]

        for hx, hy, hw, hh in highlights:
            offset_x = r.uniform(-s * 0.02, s * 0.02)
            offset_y = r.uniform(-s * 0.02, s * 0.02)
            painter.drawEllipse(QRectF(hx + offset_x, hy + offset_y, hw, hh))
