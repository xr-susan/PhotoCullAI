# PhotoCullAI

[![Python CI](https://github.com/xr-susan/PhotoCullAI/actions/workflows/python-ci.yml/badge.svg)](https://github.com/xr-susan/PhotoCullAI/actions/workflows/python-ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10 | 3.11 | 3.12](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)

**本地运行的照片/视频初筛工具：扫描一批媒体文件，给出「保留 / 废片」建议，标出相似照片组，并导出报告。**

PhotoCullAI 完全在本机运行，不上传任何文件，也不会自动删除原图。它适合先粗筛旅行照、活动照、截图、Live Photo 和短视频，再由人做最后确认。

---

## 功能特性

所有能力均在本地推理，不联网、不上传。

| 能力 | 说明 | 实现模块 |
| --- | --- | --- |
| 媒体扫描 | 递归扫描文件夹或手动选择文件，跳过 `.venv`/`.git`/`__pycache__` 等目录；支持图片与视频扩展名过滤 | `app/core/scanner.py`、`app/utils/file_utils.py` |
| 图片质量分析 | 以 85 分为基准，按模糊、过曝、欠曝、对比度、主体清晰度逐项扣分 | `app/core/analyzer.py` |
| 内容分类 | 自动判定 `portrait` / `landscape` / `text` / `screenshot`，并按类别套用不同的扣分规则 | `app/core/analyzer.py`（`infer_category`） |
| 人像专项检查 | 基于 insightface 106 关键点检测闭眼、张嘴、表情不对称、头部歪斜、姿势不协调、人脸过小/过大、遮挡 | `app/core/analyzer.py`、`app/core/face_recognition.py` |
| OCR 文字识别 | PaddleOCR 中文模型，输出平均置信度与文本块数量，用于判定文字照片与截图质量 | `app/core/analyzer.py`（`OCRService`） |
| 氛围感识别 | 低饱和 + 暖色调 + 柔和光线的照片会被识别为「氛围感」，相应扣分会被减轻，避免误杀 | `app/core/analyzer.py`（`_is_atmospheric`） |
| 相似照片分组 | pHash + dHash + aHash 三哈希投票，接近时用归一化互相关复核；并查集实现传递性分组，自动推荐组内最高分 | `app/core/duplicates.py`、`app/core/union_find.py` |
| 连拍/同文件补充分组 | 相同「文件大小 + 扩展名」视为同一文件；同一目录下 EXIF 拍摄时间相差 3 秒内的连拍归为相似组 | `app/core/duplicates.py` |
| 视频分析 | 每 30 帧采样、最多 12 帧，统计平均模糊度与曝光，输出视频评分 | `app/core/video_analyzer.py` |
| Live Photo 配对 | 同目录下同名（stem）的图片与 `.mov` 自动配对，按「封面 60% + 动态 40%」合成评分 | `app/core/livephoto.py` |
| 人物聚类 | 对 512 维人脸特征做余弦相似度聚类（阈值 0.45），按「人物一 / 人物二 …」分组浏览 | `app/core/face_recognition.py`（`cluster_faces`） |
| 缩略图网格 | 按人物分组、相似组分隔展示，异步分批加载缩略图，窗口缩放时自动重排 | `app/ui/thumbnail_grid.py`、`app/ui/thumbnail_card.py` |
| 目录树筛选 | 左侧目录树显示各目录数量，并带「人物分组」节点，可一键筛选某个人的全部照片 | `app/ui/directory_tree.py` |
| 预览对话框 | 支持缩放（5%–800%）、拖动平移、左右旋转 90°、上一张/下一张、键盘快捷键 | `app/ui/preview_dialog.py` |
| 批量操作 | 批量保留、移动到废片箱、永久删除、一键选择废片、一键保留每组最佳、停止扫描 | `app/ui/main_window.py` |
| 报告导出 | 导出 CSV / JSON / 摘要 JSON，含总数、废片数、相似组、预计可释放空间 | `app/ui/main_window.py`、`app/core/summary.py` |
| 拖拽上传 | 直接把文件夹或文件拖进窗口即可开始分析 | `app/ui/main_window.py`（`DropTargetWidget`） |
| 崩溃日志 | 主线程与子线程的未捕获异常都会写入项目根目录的 `crash.log` | `main.py` |
| 启动自检 | 启动时检查 PyQt6 / cv2 / numpy / PIL / pillow_heif，缺失则弹窗提示安装命令 | `app/utils/env_check.py` |

### 报告输出

点击「导出报告」后在 `data/reports/` 生成三个文件：

| 文件 | 内容 |
| --- | --- |
| `photo_cull_report.csv` | 逐项结果，UTF-8 BOM 编码，可直接用 Excel 打开 |
| `photo_cull_report.json` | 完整逐项结果（已剔除人脸特征向量，避免文件膨胀） |
| `photo_cull_summary.json` | 汇总：`total` / `keep` / `review` / `junk`、`media_types`、`categories`、`duplicate_groups`、`duplicate_items`、`duplicate_junk`、`estimated_reclaimable`、`missing_files` |

### 键盘快捷键

| 快捷键 | 作用 |
| --- | --- |
| `Ctrl+O` | 选择文件夹 |
| `Ctrl+E` | 导出报告 |
| `Ctrl+A` | 全选当前可见照片 |
| `Delete` | 永久删除已勾选项 |

预览窗口中：`←` / `→` 切换上一张/下一张，`+` / `-` 缩放，`0` 适应窗口，`Esc` 关闭。

---

## 界面截图

> **截图尚未提交。** 由于界面需要在 Windows 桌面环境下运行才能截取，请按下表手动截图，然后把 PNG 放到 `docs/screenshots/` 目录中，最后把下表中对应的 `![...]` 行取消注释即可。

<!--
使用方法：
1. 在仓库根目录新建 docs/screenshots/ 目录
2. 按下表命名截图文件并放入该目录
3. 删除下方示例图片行外层的 HTML 注释标记，图片即可正常显示
   （注释标记是左尖括号+感叹号+两个连字符，以及两个连字符+右尖括号）
-->

| 截图内容 | 建议文件名 | 说明 |
| --- | --- | --- |
| 主界面全貌 | `docs/screenshots/main-window.png` | 展示工具栏、统计面板、左侧目录树与缩略图网格的整体布局 |
| 扫描进度 | `docs/screenshots/scan-progress.png` | 扫描进行中的进度条与状态文案 |
| 相似照片分组 | `docs/screenshots/duplicate-groups.png` | 展示「相似组 #1 · N 张相似照片」分隔条与「最佳 · 建议保留」徽标 |
| 人物分组 | `docs/screenshots/person-groups.png` | 展示「人物一 · N 张照片」分隔条与全选按钮 |
| 照片预览 | `docs/screenshots/preview-dialog.png` | 展示预览窗口的缩放/旋转工具条与下方信息面板 |
| 导出报告结果 | `docs/screenshots/export-report.png` | 展示导出完成弹窗或 `data/reports/` 目录下的三个报告文件 |

<!-- 取消注释后即可显示图片，例如：
![主界面](docs/screenshots/main-window.png)
![相似照片分组](docs/screenshots/duplicate-groups.png)
-->

截图建议使用 Windows 的 `Win + Shift + S` 或 `Win + PrtScn`，窗口最大化后截取，避免暴露私人照片内容。

---

## 安装

需要 **Python 3.10 / 3.11 / 3.12**（CI 在这三个版本上验证）。

### 三个 requirements 文件的区别

仓库里有三个依赖文件，用途不同，不要混用：

| 文件 | 内容 | 什么时候用 |
| --- | --- | --- |
| `requirements.txt` | **完整依赖**：PyQt6、numpy、opencv-python、Pillow、onnxruntime、**paddleocr + paddlepaddle**、imagehash、**insightface**、PyYAML、pillow-heif | 想要全部功能（人脸识别、OCR、人物聚类）。日常使用推荐这个 |
| `requirements-minimal.txt` | **精简依赖**：与上面相同的 PyQt6 / numpy / opencv-python / Pillow / onnxruntime / imagehash / PyYAML / pillow-heif，但**去掉了 paddleocr、paddlepaddle、insightface**（文件头注释同时提到 MediaPipe） | 只想跑基础质量分析、相似照片检测、视频分析；或环境装不上 PaddlePaddle / InsightFace 时。CI 用的就是这个文件 |
| `requirements-build.txt` | **只有一个包**：`pyinstaller>=6.8.0` | 只在打包成 exe 时需要，由 `build_exe.bat` 自动安装 |

使用精简依赖时，**OCR 文字识别与人脸相关能力（闭眼检测、表情分析、人物聚类）会被禁用**，其余功能正常。代码里对这两个依赖都做了 `try/except` 降级处理，不会因为缺包而崩溃。

### 推荐安装步骤（Windows PowerShell）

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果只想跑基础功能：

```powershell
python -m pip install -r requirements-minimal.txt
```

### 关于 Windows 上安装重依赖的坑

`requirements.txt` 里最麻烦的两个包是 **paddlepaddle** 和 **insightface**，它们在 Windows 上经常装不上：

- **paddlepaddle** 需要和 Python 版本、CPU/GPU 严格匹配，官方源上不一定每个 Python 小版本都有预编译 wheel。装不上时可以先去 PaddlePaddle 官网查对应 Python 版本的安装命令，或改用 `requirements-minimal.txt`。
- **insightface** 需要编译工具链（Visual C++ Build Tools），且首次运行会下载约 300MB 的 `buffalo_l` 模型。`app/core/face_recognition.py` 里把模型下载源改成了 `ghproxy.net` 镜像，国内网络更容易成功；模型缓存在 `~/.insightface/models/buffalo_l`。
- 如果这两个包反复装不上，**直接换用 `requirements-minimal.txt`**，程序仍然可以正常启动和使用。

---

## 使用

### 从源码运行

```powershell
python main.py
```

启动时会先做依赖自检，缺少 PyQt6 / cv2 / numpy / PIL / pillow_heif 时会弹出错误框并给出安装命令。日志同时输出到控制台和项目根目录的 `crash.log`。

### 用 run.bat 运行

```bat
run.bat
```

`run.bat` 做的事情很简单：切到脚本所在目录，然后调用虚拟环境里的解释器，最后 `pause` 保留窗口：

```bat
cd /d "%~dp0"
.venv\Scripts\python.exe main.py
pause
```

注意它**硬编码了 `.venv`**。如果你的虚拟环境不叫 `.venv`，或者没有创建虚拟环境，这个脚本会失败——这种情况下直接用 `python main.py` 即可。

### 打包成 exe

```bat
build_exe.bat
```

`build_exe.bat` 的实际行为：

1. `python -m pip install --upgrade pip`
2. `python -m pip install -r requirements.txt`（完整依赖）
3. `python -m pip install -r requirements-build.txt`（安装 PyInstaller）
4. 执行 PyInstaller，参数为：

```
pyinstaller --noconfirm --clean --windowed --name PhotoCullAI ^
  --add-data "config.yaml;." ^
  --collect-all mediapipe ^
  --collect-all paddleocr ^
  --collect-all onnxruntime ^
  --collect-all PyQt6 ^
  main.py
```

各参数含义：

| 参数 | 作用 |
| --- | --- |
| `--noconfirm` | 覆盖输出目录时不询问 |
| `--clean` | 打包前清理 PyInstaller 缓存 |
| `--windowed` | 不显示控制台窗口（GUI 程序） |
| `--name PhotoCullAI` | 产物命名为 `PhotoCullAI` |
| `--add-data "config.yaml;."` | 把 `config.yaml` 一起打进包里 |
| `--collect-all <包>` | 完整收集该包的数据文件与子模块（PaddleOCR / onnxruntime / PyQt6 有大量非代码资源，必须这样收集） |
| `main.py` | 入口脚本 |

完成后产物在 `dist\PhotoCullAI.exe`。

> 小提示：脚本里有 `--collect-all mediapipe`，但 `mediapipe` 并不在任何一个 requirements 文件里。没有安装 mediapipe 时该参数通常只会告警而不会中断打包；如果你希望打包脚本与依赖完全一致，可以自行去掉这一行。

### 使用建议

- 第一次处理重要照片前，先用少量样本试跑一遍
- 批量删除前先检查「相似组」和「废片」筛选结果
- 「移动到废片箱」只是移动到项目的 `data/junk` 目录，**不等于系统回收站**；同名文件会自动加 `_1`、`_2` 后缀避免覆盖
- 「永久删除」不可恢复，确认有备份后再用
- 照片很多时按文件夹分批扫描，界面更流畅

---

## 配置

配置从 `config.yaml` 读取，加载逻辑在 `app/utils/config.py`。

**查找顺序**（命中即停）：

1. 当前工作目录下的 `config.yaml`
2. 仓库根目录的 `config.yaml`（相对 `app/utils/config.py` 向上两级）
3. 用户主目录下的 `~/config.yaml`

文件不存在或解析失败时会静默回退到内置默认值，**不会报错**。

### `app`

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `window_title` | `"PhotoCullAI"` | 主窗口标题 |

### `thresholds`（评分阈值）

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `keep_score` | `65` | 判定为「保留」的最低分；低于该分数为「废片」。图片、视频、Live Photo 共用此阈值 |
| `blur_low` | `80` | 模糊度（Laplacian 方差）低于此值视为「明显模糊」 |
| `blur_medium` | `150` | 模糊度低于此值视为「轻微模糊」 |
| `portrait_eye_closed` | `0.18` | 眼部纵横比低于此值判定为疑似闭眼 |
| `landscape_skew_deg` | `3.5` | 风景照歪斜角度超过此值判定为地平线歪斜 |
| `text_skew_deg` | `2.0` | 文字照片歪斜角度超过此值判定为文字歪斜 |
| `overexposure` | `0.18` | 高亮像素占比超过此值判定为过曝 |
| `underexposure` | `0.20` | 暗部像素占比超过此值判定为欠曝 |
| `duplicate_hamming` | `10` | 相似照片汉明距离阈值（见下方说明） |

> `duplicate_hamming` 已在 `config.yaml` 与默认值中声明，但当前 `app/core/duplicates.py` 使用的是代码内固定阈值（投票距离 ≤ 12、pHash 复核距离 ≤ 16），**并未读取该配置项**。修改它目前不会改变分组行为。

### `paths`

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `cache_dir` | `"data/cache"` | 缓存目录 |
| `reports_dir` | `"data/reports"` | 报告输出目录 |
| `junk_dir` | `"data/junk"` | 废片箱目录 |

> 这三个键同样是**已声明但未被代码读取**的默认值。实际路径在 `app/ui/main_window.py` 中写死为 `data/reports` 与 `data/junk`（均为相对当前工作目录）。因此**建议从仓库根目录启动程序**，否则报告和废片箱会生成在别处。

### `scan`

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `image_extensions` | `.jpg` `.jpeg` `.png` `.bmp` `.webp` `.tif` `.tiff` `.heic` | 识别为图片的扩展名 |
| `video_extensions` | `.mp4` `.mov` `.mkv` `.avi` `.webm` | 识别为视频的扩展名 |
| `max_workers` | `2`（仅存在于代码默认值中，`config.yaml` 未写出） | 扫描线程池并发数；小于等于 1 时会被强制改为 1 |

### 修改配置时的两个注意事项

1. **合并规则**：`_deep_merge` 只遍历默认值里已有的键。**在 `config.yaml` 里新增一个默认值中不存在的键，它会被直接丢弃**，不会生效（`tests/test_config.py::TestDeepMerge` 明确验证了这一点）。
2. **配置是单例缓存**：首次读取后结果会被缓存，修改文件需要重启程序。

---

## 项目结构

```text
PhotoCullAI/
├── main.py                    应用入口：日志、全局异常钩子、依赖自检、启动主窗口
├── config.yaml                默认阈值、路径与扫描扩展名
├── build_exe.bat              PyInstaller 打包脚本
├── run.bat                    调用 .venv 启动程序
├── requirements.txt           完整依赖（含 PaddleOCR / InsightFace）
├── requirements-minimal.txt   精简依赖（无 PaddleOCR / InsightFace）
├── requirements-build.txt     打包依赖（PyInstaller）
├── app/
│   ├── core/                  纯逻辑层，不依赖 Qt
│   │   ├── analyzer.py        图片质量评分、内容分类、OCR、人脸分析、氛围感识别
│   │   ├── duplicates.py      多哈希 + 互相关 + 文件大小 + EXIF 时间的相似照片分组
│   │   ├── face_recognition.py 共享 insightface 实例、512 维特征提取、人物聚类
│   │   ├── livephoto.py       Live Photo（图片 + .mov）配对与合成评分
│   │   ├── scanner.py         收集待分析文件、单文件分析入口（支持取消）
│   │   ├── summary.py         结果汇总统计与可读体积格式化
│   │   ├── types.py           MediaResult 数据类（含 to_dict，导出时剔除特征向量）
│   │   ├── union_find.py      并查集，用于相似组与人脸聚类的传递性合并
│   │   └── video_analyzer.py  视频抽帧、模糊/曝光统计与评分
│   ├── ui/                    PyQt6 界面层
│   │   ├── main_window.py     主窗口、工具栏、扫描线程、批量操作、报告导出
│   │   ├── thumbnail_grid.py  缩略图网格、人物/相似组分隔条
│   │   ├── thumbnail_card.py  单张缩略图卡片与异步加载队列
│   │   ├── directory_tree.py  目录树 + 人物分组筛选
│   │   ├── preview_dialog.py  预览窗口（缩放、平移、旋转、信息面板）
│   │   ├── styles.py          全局深色样式表
│   │   └── cloud_background.py 背景装饰绘制
│   └── utils/
│       ├── config.py          config.yaml 加载、深度合并、get() / get_section()
│       ├── env_check.py       启动依赖自检与安装命令提示
│       ├── file_utils.py      扩展名判定、路径规范化、递归列出媒体文件
│       └── image_utils.py     图片读取、缩放、模糊度、亮度指标、QPixmap 加载
├── tests/                     单元测试
└── data/                      运行产物目录（reports / junk 由程序创建，已在 .gitignore 中）
```

### 评分逻辑速览

- **图片**：基准 85 分，逐项扣分（如明显模糊 −30、过曝 −18、疑似闭眼 −30、未检测到人脸 −40……），最终分数限制在 0–100，≥ `keep_score` 判为保留。一张图片可能同时命中多个分类（如「人像 + 风景」），取各分类中**最高**的得分作为最终结果。
- **视频**：基准 100 分，整体模糊 −35、轻微模糊 −15、过曝 −15、欠曝 −12、关键帧少于 3 帧 −20。
- **Live Photo**：`图片分 × 0.6 + 视频分 × 0.4`。

---

## 测试

测试位于 `tests/`，采用 pytest 风格（部分文件基于 `unittest.TestCase`，pytest 可以直接收集运行）。

```powershell
python -m pytest tests -q
```

测试文件与覆盖范围：

| 文件 | 覆盖内容 |
| --- | --- |
| `tests/test_analyzer.py` | 模糊度、亮度指标、色彩丰富度、对比度、主体清晰度、分类推断、氛围感、人脸辅助函数、阈值读取、全局评分 |
| `tests/test_duplicates.py` | 并查集传递性分组、`MediaResult` 默认值与 `to_dict` 行为 |
| `tests/test_config.py` | 深度合并规则、`get()` / `get_section()`、默认值结构 |
| `tests/test_summary.py` | 体积格式化、汇总统计计数、可释放空间、缺失文件统计 |
| `tests/test_video_analyzer.py` | 视频分析异常路径、共享模糊度/亮度函数 |
| `tests/test_file_utils.py` | 路径规范化去重、媒体扩展名判定 |
| `tests/test_runtime_check.py` | 依赖自检与安装命令提示 |

CI（`.github/workflows/python-ci.yml`）在 Ubuntu 上以 Python 3.10 / 3.11 / 3.12 三个版本运行，除测试外还执行：

```powershell
black --check .
ruff check .
pre-commit run --all-files
pip-audit --progress=off
pytest tests --maxfail=1 -q
```

---

## 常见问题（FAQ）

### 1. 安装 PaddlePaddle / InsightFace 失败

`requirements.txt` 中的 `paddlepaddle` 对 Python 版本与平台匹配要求较严，`insightface` 还需要编译工具链。如果反复失败：

```powershell
python -m pip install -r requirements-minimal.txt
```

精简依赖下程序照常启动，只是 OCR 与人脸相关能力被禁用——代码里对这些依赖都做了 `try/except` 降级，不会因此崩溃。若坚持要完整功能，请先确认 Python 版本与 PaddlePaddle 官方 wheel 匹配，并安装 Visual C++ Build Tools。

### 2. 提示找不到人脸模型 / 人脸功能不可用

人脸功能依赖 `~/.insightface/models/buffalo_l` 下的 `buffalo_l` 模型（约 300MB），首次使用时会自动下载。若下载失败：

- 确认网络可访问 `ghproxy.net` 镜像（`app/core/face_recognition.py` 中已把模型源指向该镜像）
- 手动下载 `buffalo_l.zip` 放到 `~/.insightface/models/`，程序启动时会自动解压到 `buffalo_l/` 子目录
- 模型加载失败时程序不会报错退出，只是所有人脸相关评分（闭眼、表情、遮挡、人物聚类）失效，此时人像分类仍可能命中，但「未检测到清晰人脸」等扣分不会出现

### 3. 界面起不来 / 无图形界面环境下启动失败

PhotoCullAI 是 PyQt6 桌面程序，**必须有图形界面**，在纯 SSH / 容器 / CI 等无显示环境下无法启动。启动时若报缺少 `PyQt6`、`cv2`、`numpy`、`PIL`、`pillow_heif`，程序会弹出错误框并提示执行 `python -m pip install -r requirements.txt`。若完全没有任何提示也没有窗口，请检查项目根目录的 `crash.log`——主线程和子线程的未捕获异常都会记录在里面。

### 4. 扫描大量照片时很慢或界面卡顿

- 缩略图是异步分批加载的（每批 20 张），但分析本身受 CPU 限制。人脸检测与 OCR 是主要瓶颈
- 并发数由 `scan.max_workers` 控制，默认 **2**。注意该键只存在于代码默认值中，`config.yaml` 里**没有**它，需要的话请自行在 `scan:` 段下新增 `max_workers: 4` 才能生效
- 大图会先缩放到长边 1600 像素再分析；视频每 30 帧采样、最多取 12 帧
- 最实用的做法是**按文件夹分批扫描**，而不是一次性丢进整个照片库
- 扫描过程中可以点「停止扫描」，已取消的条目会被标记为废片

### 5. 报告或废片箱生成到了奇怪的位置

报告与废片箱路径在 `app/ui/main_window.py` 中写死为相对的 `data/reports` 和 `data/junk`，即**相对于当前工作目录**，而不是相对于仓库根目录。请始终从仓库根目录启动程序：

```powershell
cd <仓库根目录>
python main.py
```

### 6. 「移动到废片箱」的文件去哪了？

在项目的 `data/junk/` 目录下。这只是普通目录移动，**不是系统回收站**，不会被系统的「还原」找回。同名文件会自动重命名为 `原名_1.ext`、`原名_2.ext` 以避免覆盖。要真正清理请手动删除该目录。

---

## 路线图

- [ ] 提交主界面与各功能页的实际截图（见上方「界面截图」表）
- [ ] 让 `paths.cache_dir` / `paths.reports_dir` / `paths.junk_dir` 真正生效，替代硬编码路径
- [ ] 让 `thresholds.duplicate_hamming` 真正参与相似度判定
- [ ] 把 `scan.max_workers` 补进 `config.yaml` 并在界面上暴露
- [ ] 移除 `build_exe.bat` 中与实际依赖不符的 `--collect-all mediapipe`
- [ ] 为 `analyzer.py` / `duplicates.py` 补充端到端图片用例测试（当前以纯函数与单元测试为主）
- [ ] 增加更多报告格式（如 HTML 报告）

---

## 许可证

本项目基于 [MIT License](LICENSE) 发布，Copyright (c) 2026 xr-susan。
