from pathlib import Path
from collections import defaultdict

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem


class DirectoryTree(QTreeWidget):
    folderSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["目录", "数量"])
        self.setMinimumWidth(260)
        self.itemClicked.connect(self._on_item_clicked)
        self._path_to_item = {}

    def build(self, root_path: str, results):
        self.clear()
        self._path_to_item = {}

        root = Path(root_path).resolve()
        counts = defaultdict(int)

        for r in results:
            p = Path(r.path).resolve()
            try:
                parent = p.parent
                while True:
                    counts[str(parent)] += 1
                    if parent == root:
                        break
                    if root not in parent.parents:
                        break
                    parent = parent.parent
            except Exception:
                continue

        all_item = QTreeWidgetItem(["全部文件", str(len(results))])
        all_item.setData(0, Qt.ItemDataRole.UserRole, str(root))
        self.addTopLevelItem(all_item)
        self._path_to_item["__all__"] = all_item

        # ---- 人物分组 ----
        person_groups = defaultdict(list)
        for r in results:
            if r.person_label:
                person_groups[r.person_label].append(r)

        if person_groups:
            person_root = QTreeWidgetItem(["  人物分组", str(sum(len(v) for v in person_groups.values()))])
            person_root.setData(0, Qt.ItemDataRole.UserRole, "__person_root__")
            all_item.addChild(person_root)

            for label in sorted(person_groups.keys()):
                cnt = len(person_groups[label])
                item = QTreeWidgetItem([f"  {label}", str(cnt)])
                item.setData(0, Qt.ItemDataRole.UserRole, f"__person__{label}")
                person_root.addChild(item)
                self._path_to_item[f"__person__{label}"] = item

            self._path_to_item["__person_root__"] = person_root
            self.expandItem(person_root)

        # ---- 目录树 ----
        root_item = QTreeWidgetItem([root.name or str(root), str(counts.get(str(root), 0))])
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(root))
        all_item.addChild(root_item)
        self._path_to_item[str(root)] = root_item

        all_dirs = sorted(counts.keys(), key=lambda x: (len(Path(x).parts), x))
        for folder in all_dirs:
            if folder == str(root):
                continue
            if root not in Path(folder).parents:
                continue
            parent_path = str(Path(folder).parent)
            parent_item = self._path_to_item.get(parent_path, root_item)
            item = QTreeWidgetItem([Path(folder).name, str(counts[folder])])
            item.setData(0, Qt.ItemDataRole.UserRole, folder)
            parent_item.addChild(item)
            self._path_to_item[folder] = item

        self.expandItem(all_item)
        self.expandItem(root_item)

    def _on_item_clicked(self, item, column):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.folderSelected.emit(path)
