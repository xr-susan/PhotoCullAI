DARK_STYLE = """
/* ========== 全局基础 ========== */
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #87CEEB, stop:0.4 #B0E0FF, stop:0.7 #D4F0FF, stop:1 #E8F4FD);
}

QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #2C3E50;
}

/* ========== 按钮 ========== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #7EC8E3, stop:1 #A8D8EA);
    color: white;
    border: none;
    border-radius: 18px;
    padding: 10px 24px;
    font-weight: bold;
    font-size: 14px;
    min-height: 20px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6BB8D3, stop:1 #98C8DA);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #5BA8C3, stop:1 #88B8CA);
}

QPushButton:disabled {
    background: #C0D8E8;
    color: #8BA8B8;
}

/* ========== 标签 ========== */
QLabel {
    background: transparent;
    color: #2C3E50;
    font-size: 13px;
}

/* ========== 进度条 ========== */
QProgressBar {
    background: rgba(255, 255, 255, 0.5);
    border: none;
    border-radius: 10px;
    height: 20px;
    text-align: center;
    color: #2C3E50;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #FFB6C1, stop:0.5 #87CEEB, stop:1 #DDA0DD);
    border-radius: 10px;
}

/* ========== 滚动区域 ========== */
QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: rgba(255, 255, 255, 0.3);
    width: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(135, 206, 235, 0.6);
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(135, 206, 235, 0.9);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: rgba(255, 255, 255, 0.3);
    height: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: rgba(135, 206, 235, 0.6);
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(135, 206, 235, 0.9);
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ========== 卡片 ========== */
QFrame#thumbCard {
    background: rgba(255, 255, 255, 0.75);
    border-radius: 16px;
    border: 2px solid rgba(135, 206, 235, 0.3);
}

QFrame#thumbCard:hover {
    background: rgba(255, 255, 255, 0.9);
    border: 2px solid rgba(135, 206, 235, 0.8);
}

/* ========== 目录树 ========== */
QTreeWidget {
    background: rgba(255, 255, 255, 0.6);
    border: none;
    border-radius: 14px;
    padding: 6px;
    outline: none;
}

QTreeWidget::item {
    padding: 6px 4px;
    border-radius: 8px;
    color: #2C3E50;
}

QTreeWidget::item:hover {
    background: rgba(135, 206, 235, 0.3);
}

QTreeWidget::item:selected {
    background: rgba(135, 206, 235, 0.5);
    color: #1A5276;
    font-weight: bold;
}

QHeaderView::section {
    background: rgba(135, 206, 235, 0.4);
    color: #2C3E50;
    border: none;
    padding: 6px;
    font-weight: bold;
    border-radius: 0;
}

/* ========== 复选框 ========== */
QCheckBox {
    spacing: 8px;
    color: #2C3E50;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #87CEEB;
    background: rgba(255, 255, 255, 0.7);
}

QCheckBox::indicator:checked {
    background: #87CEEB;
    border-color: #5BA8C3;
}

/* ========== 输入框 ========== */
QLineEdit {
    background: rgba(255, 255, 255, 0.7);
    border: 2px solid rgba(135, 206, 235, 0.4);
    border-radius: 10px;
    padding: 8px 12px;
    color: #2C3E50;
    selection-background-color: #87CEEB;
}

QLineEdit:focus {
    border: 2px solid #87CEEB;
}

/* ========== 文本编辑 ========== */
QTextEdit {
    background: rgba(255, 255, 255, 0.7);
    border: 2px solid rgba(135, 206, 235, 0.3);
    border-radius: 12px;
    padding: 8px;
    color: #2C3E50;
    selection-background-color: #87CEEB;
}

/* ========== 对话框 ========== */
QDialog {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #87CEEB, stop:0.5 #B0E0FF, stop:1 #E8F4FD);
}

/* ========== 分割器 ========== */
QSplitter::handle {
    background: rgba(135, 206, 235, 0.3);
    width: 3px;
    height: 3px;
    border-radius: 1px;
}

QSplitter::handle:hover {
    background: rgba(135, 206, 235, 0.7);
}

/* ========== 消息框 ========== */
QMessageBox {
    background: #E8F4FD;
}

QMessageBox QLabel {
    color: #2C3E50;
    font-size: 14px;
}

/* ========== 文件对话框 ========== */
QFileDialog {
    background: #E8F4FD;
}

/* ========== 状态标签 ========== */
QLabel#statusLabel {
    color: #5B8C9E;
    font-size: 13px;
    padding: 4px 12px;
    background: rgba(255, 255, 255, 0.4);
    border-radius: 12px;
}

/* ========== 分数标签 ========== */
QLabel#verdictKeep {
    background: rgba(46, 204, 113, 0.2);
    color: #27AE60;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: bold;
}

QLabel#verdictReview {
    background: rgba(241, 196, 15, 0.2);
    color: #D4A017;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: bold;
}

QLabel#verdictJunk {
    background: rgba(231, 76, 60, 0.2);
    color: #E74C3C;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: bold;
}

/* ========== 预览对话框 ========== */
QFrame#previewInfo {
    background: rgba(255, 255, 255, 0.7);
    border-radius: 14px;
    padding: 12px;
}

QLabel#previewTitle {
    font-size: 16px;
    font-weight: bold;
    color: #1A5276;
}

QLabel#previewValue {
    color: #2C3E50;
    font-size: 13px;
}

QLabel#previewNavBtn {
    background: rgba(135, 206, 235, 0.5);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 18px;
    color: white;
    font-weight: bold;
}

QLabel#previewNavBtn:hover {
    background: rgba(135, 206, 235, 0.8);
}
"""
