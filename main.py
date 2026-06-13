import logging
import sys
import traceback
import threading
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

from app.ui.main_window import MainWindow
from app.utils.env_check import format_install_command, get_missing_dependencies

# 日志文件写入项目目录
LOG_FILE = Path(__file__).parent / "crash.log"

# 全局异常钩子：主线程未捕获异常
def _global_excepthook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical("未捕获异常（主线程）:\n%s", msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n[主线程未捕获异常]\n{msg}\n")
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)

# 全局异常钩子：子线程未捕获异常
def _threading_excepthook(args):
    msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_tb))
    logging.critical("未捕获异常（子线程 %s):\n%s", args.thread, msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n[子线程未捕获异常] thread={args.thread}\n{msg}\n")
    except Exception:
        pass

sys.excepthook = _global_excepthook
threading.excepthook = _threading_excepthook


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        ]
    )
    # PIL 调试信息太多，单独降级
    pil_logger = logging.getLogger("PIL")
    pil_logger.setLevel(logging.WARNING)
    pil_logger.propagate = False
    app = QApplication(sys.argv)
    app.setApplicationName("PhotoCullAI")

    missing = get_missing_dependencies()
    if missing:
        QMessageBox.critical(
            None,
            "环境检查失败",
            "当前环境缺少关键依赖，程序无法启动。\n\n"
            f"缺失项：{', '.join(missing)}\n\n"
            f"请执行：{format_install_command()}"
        )
        return 1

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
