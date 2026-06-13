import csv
import json
import logging
import os
import shutil
import threading
import traceback
from pathlib import Path
from queue import Queue

logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QFileDialog, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMessageBox, QSplitter, QProgressBar, QFrame,
    QGroupBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QKeySequence, QShortcut

from app.ui.styles import DARK_STYLE
from app.ui.cloud_background import CloudBackground
from app.ui.thumbnail_grid import ThumbnailGrid
from app.ui.preview_dialog import PreviewDialog
from app.ui.directory_tree import DirectoryTree
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.core.scanner import collect_media_files, analyze_one
from app.core.duplicates import apply_duplicate_policy
from app.core.types import MediaResult
from app.utils.file_utils import normalize_input_paths, is_supported_media_path
from app.utils.config import get
from app.core.face_recognition import cluster_faces, get_person_name


class DropTargetWidget(QWidget):
    def __init__(self, on_drop=None, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.on_drop = on_drop

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            return
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        if paths and self.on_drop:
            event.acceptProposedAction()
            self.on_drop(paths)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(get("app", "window_title", "PhotoCullAI"))
        self.resize(1700, 1000)
        self.setStyleSheet(DARK_STYLE)
        self.setAcceptDrops(True)

        self.all_results = []
        self.current_root = ""
        self.current_filter = ""
        self._person_filter = ""

        self._scan_thread = None
        self._scan_queue = Queue()
        self._scan_total = 0
        self._scan_done = False
        self._cancel_event = threading.Event()
        self._media_list = []
        self._media_index = 0
        self._scan_errors = []

        self.cloud_bg = CloudBackground(self)

        root = DropTargetWidget(on_drop=self.handle_dropped_paths)
        self.setCentralWidget(root)
        root.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setStyleSheet("""
            QFrame#toolbar {
                background: rgba(255, 255, 255, 0.55);
                border-radius: 18px;
                padding: 10px 16px;
            }
        """)
        top = QHBoxLayout(toolbar)
        top.setContentsMargins(12, 8, 12, 8)
        top.setSpacing(10)

        self.btn_select = QPushButton("选择文件夹")
        self.btn_select.clicked.connect(self.select_folder)

        self.btn_upload = QPushButton("上传照片/视频")
        self.btn_upload.clicked.connect(self.upload_photos)

        self.btn_export = QPushButton("导出报告")
        self.btn_export.clicked.connect(self.export_report)

        self.btn_keep = QPushButton("批量保留")
        self.btn_keep.clicked.connect(self.batch_keep)

        self.btn_junk = QPushButton("移动到废片箱")
        self.btn_junk.clicked.connect(self.batch_move_junk)

        self.btn_auto_junk = QPushButton("一键选择废片")
        self.btn_auto_junk.clicked.connect(self.auto_select_junk)

        self.btn_keep_best = QPushButton("一键保留最佳")
        self.btn_keep_best.clicked.connect(self.keep_best_in_groups)

        self.btn_delete = QPushButton("永久删除")
        self.btn_delete.clicked.connect(self.batch_delete)

        self.btn_cancel = QPushButton("停止扫描")
        self.btn_cancel.clicked.connect(self.cancel_scan)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #E74C3C, stop:1 #C0392B);
                color: white;
                border: none;
                border-radius: 18px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #C0392B; }
            QPushButton:disabled { background: #D5B8B8; color: #A08080; }
        """)

        self.status = QLabel("支持选择文件夹或照片/视频，拖拽到窗口上传")
        self.status.setObjectName("statusLabel")

        top.addWidget(self.btn_select)
        top.addWidget(self.btn_upload)
        top.addWidget(self.btn_export)
        top.addWidget(self.btn_keep)
        top.addWidget(self.btn_junk)
        top.addWidget(self.btn_auto_junk)
        top.addWidget(self.btn_keep_best)
        top.addWidget(self.btn_delete)
        top.addWidget(self.btn_cancel)
        top.addStretch()
        top.addWidget(self.status)
        layout.addWidget(toolbar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("扫描进度：%v / %m")
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # 统计面板
        stats_frame = QFrame()
        stats_frame.setObjectName("toolbar")
        stats_frame.setStyleSheet("""
            QFrame#toolbar {
                background: rgba(255, 255, 255, 0.55);
                border-radius: 18px;
                padding: 10px 16px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(12, 6, 12, 6)
        stats_layout.setSpacing(24)

        self.lbl_total = QLabel("总计：0")
        self.lbl_total.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lbl_keep = QLabel("保留：0")
        self.lbl_keep.setStyleSheet("color: #27AE60; font-weight: bold; font-size: 14px;")
        self.lbl_junk = QLabel("废片：0")
        self.lbl_junk.setStyleSheet("color: #E74C3C; font-weight: bold; font-size: 14px;")
        self.lbl_persons = QLabel("")
        self.lbl_persons.setStyleSheet("color: #5B8C9E; font-size: 13px;")

        for lbl in [self.lbl_total, self.lbl_keep, self.lbl_junk, self.lbl_persons]:
            stats_layout.addWidget(lbl)
        stats_layout.addStretch()
        layout.addWidget(stats_frame)

        self.tree = DirectoryTree()
        self.tree.folderSelected.connect(self.apply_folder_filter)

        self.grid = ThumbnailGrid(on_open=self.open_preview)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.grid)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter)

        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_results)
        self._poll_timer.setInterval(100)  # 30ms → 100ms，降低 UI 刷新开销

        self._set_buttons_enabled(True)

        # 快捷键
        QShortcut(QKeySequence("Ctrl+O"), self, self.select_folder)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_report)
        QShortcut(QKeySequence("Delete"), self, self.batch_delete)
        QShortcut(QKeySequence("Ctrl+A"), self, self._select_all_visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.cloud_bg.resize(self.size())

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder:
            return
        self.start_scan([folder])

    def upload_photos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "上传照片/视频", "",
            "图片和视频 (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.heic *.mp4 *.mov *.mkv *.avi *.webm);;所有文件 (*)"
        )
        if not files:
            return
        self.start_scan(files)

    def handle_dropped_paths(self, paths):
        normalized = normalize_input_paths(paths)
        if not normalized:
            self.status.setText("拖拽的路径无效")
            return
        self.start_scan(normalized)

    def start_scan(self, inputs):
        if self._scan_thread and self._scan_thread.is_alive():
            QMessageBox.information(self, "提示", "正在扫描中，请等待完成")
            return

        normalized = normalize_input_paths(inputs)
        if not normalized:
            self.status.setText("路径无效")
            return

        valid_inputs = [p for p in normalized if Path(p).is_dir() or is_supported_media_path(p)]
        if not valid_inputs:
            QMessageBox.warning(self, "提示",
                "没有找到支持的图片或视频文件\n\n"
                "图片：jpg, jpeg, png, bmp, webp, tif, tiff, heic\n"
                "视频：mp4, mov, mkv, avi, webm")
            return

        self.all_results = []
        self.grid.clear()
        self.current_root = ""
        self.current_filter = ""
        self._cancel_event.clear()

        self._media_list = collect_media_files(valid_inputs)
        self._scan_total = len(self._media_list)
        self._media_index = 0
        self._scan_done = False
        self._scan_errors = []

        if self._scan_total == 0:
            self.status.setText("未找到支持的图片或视频文件")
            return

        self._set_buttons_enabled(False)
        self.progress_bar.setMaximum(self._scan_total)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status.setText(f"开始分析 {self._scan_total} 个文件...")

        self._scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
        self._scan_thread.start()

        self._poll_timer.start()

    def _scan_worker(self):
        max_workers = get("scan", "max_workers", 2)
        if max_workers <= 1:
            max_workers = 1

        def _analyze(item):
            if self._cancel_event.is_set():
                name = item[1] if isinstance(item, tuple) else item
                return MediaResult(
                    path=name, media_type="unknown", category="unknown",
                    score=0.0, verdict="junk", reason="已取消扫描"
                )
            try:
                return analyze_one(item, cancel_event=self._cancel_event)
            except Exception as exc:
                logging.exception("扫描线程异常：%s", item)
                name = item[1] if isinstance(item, tuple) else item
                return MediaResult(
                    path=str(name), media_type="unknown", category="unknown",
                    score=0.0, verdict="review", reason=f"分析异常: {exc}"
                )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_analyze, item): item for item in self._media_list}
            for future in as_completed(futures):
                if self._cancel_event.is_set():
                    break
                try:
                    result = future.result()
                    self._scan_queue.put(result)
                except Exception as exc:
                    item = futures[future]
                    logging.exception("并发扫描异常：%s", item)
                    name = item[1] if isinstance(item, tuple) else item
                    self._scan_queue.put(MediaResult(
                        path=str(name), media_type="unknown", category="unknown",
                        score=0.0, verdict="review", reason=f"分析异常: {exc}"
                    ))
        self._scan_done = True

    def _poll_results(self):
        count = 0
        while not self._scan_queue.empty() and count < 10:
            try:
                result = self._scan_queue.get_nowait()
            except Exception:
                break

            self.all_results.append(result)
            self.grid.append_result(result)

            if not self.current_root:
                try:
                    self.current_root = str(Path(result.path).parent)
                    self.current_filter = self.current_root
                except Exception:
                    logger.debug("设置 current_root 失败: %s", result.path, exc_info=True)

            self._media_index += 1
            count += 1

        if self._media_index > 0:
            self.progress_bar.setValue(self._media_index)
            name = Path(self.all_results[-1].path).name
            if len(name) > 35:
                name = name[:32] + "..."
            self.status.setText(f"正在分析 ({self._media_index}/{self._scan_total}): {name}")

        if self._scan_done and self._scan_queue.empty():
            self._poll_timer.stop()
            self._on_scan_complete()

    def _on_scan_complete(self):
        apply_duplicate_policy(self.all_results)

        # 人脸特征聚类，按人物分组
        face_data = []
        for r in self.all_results:
            if r.face_embedding is not None:
                face_data.append((r.path, r.face_embedding))
        if face_data:
            clusters = cluster_faces(face_data)
            for r in self.all_results:
                if r.path in clusters:
                    idx = clusters[r.path]
                    r.person_label = get_person_name(idx)
                # 清理内存中的 embedding
                r.face_embedding = None

        self.all_results.sort(key=lambda r: r.score, reverse=True)
        if self.all_results:
            try:
                paths = [r.path for r in self.all_results]
                self.current_root = os.path.commonpath(paths)
            except Exception:
                if self.all_results:
                    self.current_root = str(Path(self.all_results[0].path).parent)
            self.current_filter = self.current_root
            self.tree.build(self.current_root, self.all_results)

        self._refresh_stats()
        count = len(self.all_results)
        person_count = len({r.person_label for r in self.all_results if r.person_label})
        person_info = f"，识别到 {person_count} 个人物" if person_count else ""
        cancelled = "（已部分取消）" if self._cancel_event.is_set() else ""
        if self._scan_errors:
            self.status.setText(
                f"扫描完成{cancelled}：共 {count} 个文件{person_info}；{len(self._scan_errors)} 个文件分析异常，已标记为待审核"
            )
        else:
            self.status.setText(f"扫描完成{cancelled}：共 {count} 个文件{person_info}")
        self.progress_bar.hide()
        self._set_buttons_enabled(True)

    def cancel_scan(self):
        self._cancel_event.set()
        self.btn_cancel.setEnabled(False)
        self.status.setText("正在停止扫描…")

    def _set_buttons_enabled(self, enabled):
        self.btn_select.setEnabled(enabled)
        self.btn_upload.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
        self.btn_keep.setEnabled(enabled)
        self.btn_junk.setEnabled(enabled)
        self.btn_auto_junk.setEnabled(enabled)
        self.btn_keep_best.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)
        self.btn_cancel.setEnabled(not enabled)

    def get_filtered_results(self):
        if not self.current_filter:
            return self.all_results
        root = Path(self.current_filter).resolve()
        root_str = str(root) + os.sep
        out = []
        for r in self.all_results:
            try:
                p_str = str(Path(r.path).resolve())
                if p_str == root or p_str.startswith(root_str):
                    out.append(r)
            except Exception:
                logger.debug("路径解析失败，已跳过: %s", r.path, exc_info=True)
        return out

    def apply_folder_filter(self, folder_path):
        self.current_filter = folder_path
        self._person_filter = ""  # 默认清除人物筛选

        if folder_path.startswith("__person__"):
            # 人物筛选
            self._person_filter = folder_path[len("__person__"):]
            filtered = [r for r in self.all_results if r.person_label == self._person_filter]
            self.grid.set_results(filtered)
            self.status.setText(f"当前筛选：{self._person_filter}（{len(filtered)} 张）")
        elif folder_path == "__person_root__":
            # 点击人物分组根节点，显示所有有人物标签的
            filtered = [r for r in self.all_results if r.person_label]
            self.grid.set_results(filtered)
            self.status.setText(f"当前筛选：所有人物（{len(filtered)} 张）")
        else:
            self.grid.set_results(self.get_filtered_results())
            self.status.setText(f"当前筛选：{folder_path}")

    def open_preview(self, result: MediaResult):
        visible = self.get_filtered_results()
        dialog = PreviewDialog(result, visible, self)
        dialog.exec()

    def export_report(self):
        if not self.all_results:
            QMessageBox.information(self, "提示", "没有扫描结果，请先扫描照片")
            return

        out_dir = Path("data/reports")
        out_dir.mkdir(parents=True, exist_ok=True)

        csv_path = out_dir / "photo_cull_report.csv"
        json_path = out_dir / "photo_cull_report.json"

        try:
            rows = [r.to_dict() for r in self.all_results]
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "导出完成", f"报告已导出到：\n{csv_path}\n{json_path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出报告时出错：{e}")

    def batch_keep(self):
        selected = self.grid.selected_results()
        if not selected:
            QMessageBox.information(self, "提示", "请先勾选要保留的照片")
            return

        selected_paths = {r.path for r in selected}
        count = 0
        for r in self.all_results:
            if r.path in selected_paths:
                r.verdict = "keep"
                if "已人工批量保留" not in r.reason:
                    r.reason += "；已人工批量保留"
                count += 1

        self.refresh_views()
        self.status.setText(f"已批量保留：{count} 项")

    def batch_move_junk(self):
        selected = self.grid.selected_results()
        if not selected:
            QMessageBox.information(self, "提示", "请先勾选要移动到废片箱的照片")
            return

        reply = QMessageBox.question(
            self, "确认移动",
            f"确定要将 {len(selected)} 个文件移动到废片箱吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        junk_dir = Path("data/junk")
        junk_dir.mkdir(parents=True, exist_ok=True)

        moved = 0
        selected_paths = {r.path for r in selected}
        remain = []

        for r in self.all_results:
            if r.path not in selected_paths:
                remain.append(r)
                continue
            src = Path(r.path)
            if not src.exists():
                continue
            dst = junk_dir / src.name
            i = 1
            while dst.exists():
                dst = junk_dir / f"{src.stem}_{i}{src.suffix}"
                i += 1
            try:
                shutil.move(str(src), str(dst))
                moved += 1
            except Exception:
                remain.append(r)

        self.all_results = remain
        self.refresh_views()
        self.status.setText(f"已移动到废片箱：{moved} 项")

    def auto_select_junk(self):
        self.grid.select_by_verdict("junk")
        junk_count = sum(1 for c in self.grid.cards if c.result.verdict == "junk")
        self.status.setText(f"已自动选择 {junk_count} 张废片")

    def keep_best_in_groups(self):
        """一键保留每组相似照片中的最佳照片，选中其余照片"""
        if not self.all_results:
            QMessageBox.information(self, "提示", "没有扫描结果")
            return

        # 找出所有相似组
        groups = {}
        for r in self.all_results:
            if r.duplicate_group >= 0:
                groups.setdefault(r.duplicate_group, []).append(r)

        if not groups:
            QMessageBox.information(self, "提示", "没有相似照片组")
            return

        keep_count = 0
        select_count = 0

        for gid, members in groups.items():
            # 按分数排序，最高分为最佳
            members.sort(key=lambda r: r.score, reverse=True)
            best = members[0]
            # 标记最佳为保留
            best.verdict = "keep"
            if "已人工保留最佳" not in best.reason:
                best.reason += "；已人工保留最佳"
            keep_count += 1
            # 非最佳的标记为废片
            for r in members[1:]:
                r.verdict = "junk"
                if "相似图非最佳" not in r.reason:
                    r.reason += "；相似图非最佳"
                select_count += 1

        self.refresh_views()
        # 自动勾选非最佳的
        self.grid.select_by_verdict("junk")
        self.status.setText(f"已保留 {keep_count} 张最佳照片，选中 {select_count} 张相似重复照片待删除")

    def batch_delete(self):
        selected = self.grid.selected_results()
        if not selected:
            QMessageBox.information(self, "提示", "请先勾选要删除的照片")
            return

        non_keep = [r for r in selected if r.verdict != "keep"]

        msg = f"确定要永久删除 {len(selected)} 个文件吗？\n\n此操作不可恢复！"
        if non_keep:
            msg += f"\n\n注意：其中有 {len(non_keep)} 个是保留照片"

        reply = QMessageBox.warning(
            self, "确认永久删除", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted = 0
        selected_paths = {r.path for r in selected}
        remain = []

        for r in self.all_results:
            if r.path not in selected_paths:
                remain.append(r)
                continue
            src = Path(r.path)
            if not src.exists():
                deleted += 1
                continue
            try:
                src.unlink()
                deleted += 1
            except Exception:
                remain.append(r)

        self.all_results = remain
        self.refresh_views()
        self.status.setText(f"已永久删除：{deleted} 项")

    def refresh_views(self):
        if self.current_root:
            self.tree.build(self.current_root, self.all_results)
        self.grid.set_results(self.get_filtered_results())
        self._refresh_stats()

    def _refresh_stats(self):
        total = len(self.all_results)
        keep = sum(1 for r in self.all_results if r.verdict == "keep")
        junk = sum(1 for r in self.all_results if r.verdict == "junk")
        self.lbl_total.setText(f"总计：{total}")
        self.lbl_keep.setText(f"保留：{keep}")
        self.lbl_junk.setText(f"废片：{junk}")
        person_count = len({r.person_label for r in self.all_results if r.person_label})
        self.lbl_persons.setText(f"人物：{person_count}" if person_count else "")

    def _select_all_visible(self):
        for card in self.grid.cards:
            card.checkbox.setChecked(True)
