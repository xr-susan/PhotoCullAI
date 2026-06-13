from pathlib import Path

from PyQt6.QtWidgets import QWidget, QGridLayout, QScrollArea, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QPushButton
from PyQt6.QtCore import Qt

from app.ui.thumbnail_card import ThumbnailCard


class GroupSeparator(QFrame):
    """相似照片组分隔标签"""
    def __init__(self, group_id, count, best_name="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        best_info = f"  最佳: {best_name}  " if best_name else "  "
        label = QLabel(
            f"  相似组 #{group_id + 1}  ·  {count} 张相似照片  ·  "
            f"建议保留最佳 1 张，删除其余 {count - 1} 张  {best_info}"
        )
        label.setStyleSheet(
            "color: #C0392B; font-size: 13px; font-weight: bold; "
            "background: rgba(231,76,60,0.08); border-radius: 10px; padding: 4px 12px;"
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch()


class PersonSeparator(QFrame):
    """人物分组标签，带全选按钮"""
    def __init__(self, person_name, count, on_select_all=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setObjectName("personSeparator")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        icon = QLabel(" ")
        icon.setStyleSheet("font-size: 16px; background: transparent;")
        layout.addWidget(icon)

        label = QLabel(f"{person_name}  ·  {count} 张照片")
        label.setStyleSheet(
            "color: #1A5276; font-size: 14px; font-weight: bold; "
            "background: rgba(135,206,235,0.12); border-radius: 10px; padding: 4px 12px;"
        )
        layout.addWidget(label)

        layout.addStretch()

        btn = QPushButton(f"全选{person_name}")
        btn.setFixedHeight(32)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #87CEEB, stop:1 #A8D8EA);
                color: white;
                border: none;
                border-radius: 14px;
                padding: 4px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6BB8D3, stop:1 #98C8DA);
            }
        """)
        if on_select_all:
            btn.clicked.connect(on_select_all)
        layout.addWidget(btn)


class ThumbnailGrid(QScrollArea):
    def __init__(self, on_open=None, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.on_open = on_open

        self.container = QWidget()
        self.setWidget(self.container)

        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.grid_widget = QWidget()
        self.layout = QGridLayout(self.grid_widget)
        self.layout.setSpacing(12)
        self.main_layout.addWidget(self.grid_widget)

        self.placeholder = QLabel("拖拽文件夹或照片到此处开始分析")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet(
            "color: rgba(44,62,80,0.4); font-size: 18px; padding: 80px;"
        )
        self.main_layout.addWidget(self.placeholder)

        self.cards = []
        self._columns = 5
        self._extra_widgets = []  # 分隔标签等额外 widget

    def clear(self):
        self.cards = []
        for w in self._extra_widgets:
            w.deleteLater()
        self._extra_widgets = []
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_results(self, results):
        self.clear()
        if not results:
            self.placeholder.show()
            self.grid_widget.hide()
            return

        self.placeholder.hide()
        self.grid_widget.show()

        self._columns = max(1, (self.viewport().width() - 20) // 240)

        # 按人物分组
        person_groups = {}  # person_label -> [result, ...]
        no_person = []
        for r in results:
            if r.person_label:
                person_groups.setdefault(r.person_label, []).append(r)
            else:
                no_person.append(r)

        row = 0
        col = 0

        # 先显示每个人物组
        if person_groups:
            # 按人物名称排序（人物一、人物二...）
            sorted_persons = sorted(person_groups.items(), key=lambda x: results.index(x[1][0]))
            for person_name, person_results in sorted_persons:
                # 按分数排序
                person_results.sort(key=lambda r: r.score, reverse=True)

                # 插入人物分隔标签（带全选按钮）
                sep = PersonSeparator(
                    person_name, len(person_results),
                    on_select_all=lambda checked=False, p=person_name: self.select_by_person(p)
                )
                self._extra_widgets.append(sep)
                self.layout.addWidget(sep, row, 0, 1, self._columns)
                row += 1
                col = 0

                # 在人物组内，分离相似组和非相似
                dup_groups = {}
                singles = []
                for r in person_results:
                    if r.duplicate_group >= 0:
                        dup_groups.setdefault(r.duplicate_group, []).append(r)
                    else:
                        singles.append(r)

                # 显示相似组
                group_counter = 0
                for gid, members in dup_groups.items():
                    if len(members) > 1:
                        members.sort(key=lambda r: r.score, reverse=True)
                        best_name = Path(members[0].path).name
                        sep = GroupSeparator(group_counter, len(members), best_name=best_name)
                        self._extra_widgets.append(sep)
                        self.layout.addWidget(sep, row, 0, 1, self._columns)
                        row += 1
                        col = 0
                        group_counter += 1

                    for result in members:
                        card = ThumbnailCard(result, on_open=self.on_open)
                        self.cards.append(card)
                        self.layout.addWidget(card, row, col)
                        col += 1
                        if col >= self._columns:
                            col = 0
                            row += 1

                    if len(members) > 1 and col > 0:
                        col = 0
                        row += 1

                # 显示非相似照片
                for result in singles:
                    card = ThumbnailCard(result, on_open=self.on_open)
                    self.cards.append(card)
                    self.layout.addWidget(card, row, col)
                    col += 1
                    if col >= self._columns:
                        col = 0
                        row += 1

                # 人物组结束后换行
                if col > 0:
                    col = 0
                    row += 1

        # 显示无人物标签的照片（风景、文字等）
        if no_person:
            no_person.sort(key=lambda r: r.score, reverse=True)

            # 分离相似组和非相似
            dup_groups = {}
            singles = []
            for r in no_person:
                if r.duplicate_group >= 0:
                    dup_groups.setdefault(r.duplicate_group, []).append(r)
                else:
                    singles.append(r)

            # 显示相似组
            group_counter = 0
            for gid, members in dup_groups.items():
                if len(members) > 1:
                    members.sort(key=lambda r: r.score, reverse=True)
                    best_name = Path(members[0].path).name
                    sep = GroupSeparator(group_counter, len(members), best_name=best_name)
                    self._extra_widgets.append(sep)
                    self.layout.addWidget(sep, row, 0, 1, self._columns)
                    row += 1
                    col = 0
                    group_counter += 1

                for result in members:
                    card = ThumbnailCard(result, on_open=self.on_open)
                    self.cards.append(card)
                    self.layout.addWidget(card, row, col)
                    col += 1
                    if col >= self._columns:
                        col = 0
                        row += 1

                if len(members) > 1 and col > 0:
                    col = 0
                    row += 1

            # 显示非相似照片
            for result in singles:
                card = ThumbnailCard(result, on_open=self.on_open)
                self.cards.append(card)
                self.layout.addWidget(card, row, col)
                col += 1
                if col >= self._columns:
                    col = 0
                    row += 1

        self._current_row = row + (1 if col > 0 else 0)
        self._current_col = col

    def append_result(self, result):
        if not self.grid_widget.isVisible():
            self.placeholder.hide()
            self.grid_widget.show()

        self._columns = max(1, (self.viewport().width() - 20) // 240)
        card = ThumbnailCard(result, on_open=self.on_open)
        self.cards.append(card)
        idx = len(self.cards) - 1
        row = idx // self._columns
        col = idx % self._columns
        self.layout.addWidget(card, row, col)

    def selected_results(self):
        return [c.result for c in self.cards if c.checkbox.isChecked()]

    def select_by_verdict(self, verdict):
        for card in self.cards:
            card.checkbox.setChecked(card.result.verdict == verdict)

    def select_by_person(self, person_label):
        """全选指定人物的所有照片"""
        for card in self.cards:
            if card.result.person_label == person_label:
                card.checkbox.setChecked(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.cards:
            self._relayout()

    def _relayout(self):
        new_cols = max(1, (self.viewport().width() - 20) // 240)
        if new_cols == self._columns:
            return
        self._columns = new_cols
        # 仅移动卡片位置，不重新创建
        for i, card in enumerate(self.cards):
            self.layout.addWidget(card, i // self._columns, i % self._columns)
