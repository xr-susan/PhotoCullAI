# GitHub 仓库元数据（待手动填写）

> **这是给仓库主人的备忘，不是给程序读的配置文件。**
>
> 本文件包含建议填写到 GitHub 仓库设置中的**描述**与**话题（topics）**。GitHub 无法通过仓库内的文件自动设置这两项，需要手动粘贴：
>
> - **描述**：仓库主页右上角 **About** → 齿轮图标 → **Description** → 粘贴后保存
> - **话题**：同一个 About 面板 → **Topics** → 逐个粘贴（GitHub 话题必须小写、用连字符分隔）
>
> 当前仓库这两项均为空，因此在仓库列表中显示为空白。填完即可解决。

---

## 建议的仓库描述（Repository description）

长度 116 字符，结尾无句号。

> 关于长度：GitHub 描述字段的**输入上限是 350 字符**，但**显示时会在不同位置被截断**——搜索结果约 100–130 字符、个人主页置顶卡片约 100–120 字符、仓库列表约 140–160 字符，链接预览各平台不同。所以真正要紧的是**前 90–100 字符**必须说清「是什么、给谁用」。本描述的前 100 字符已经交代了「本地 PyQt6 桌面应用 + 扫描照片/视频库」，符合这个要求。

```text
Local PyQt6 desktop app to scan photo/video libraries, score quality, group near-duplicates, and export cull reports
```

备选（更短，突出「本地、不上传」的卖点）：

```text
Local-only PyQt6 desktop app that scores photo quality, groups near-duplicates, and exports cull reports
```

---

## 建议的话题（Topics）

共 15 个，全部小写、以连字符分隔，可直接逐条粘贴：

```text
python
pyqt6
photo-culling
photo-management
duplicate-detection
image-quality
computer-vision
opencv
insightface
paddleocr
face-recognition
live-photos
video-analysis
desktop-application
imagehash
```

### 话题选取理由

| 话题 | 依据 |
| --- | --- |
| `python` | 项目语言，CI 覆盖 Python 3.10 / 3.11 / 3.12 |
| `pyqt6` | 界面层 `app/ui/` 全部基于 PyQt6 |
| `photo-culling` | 项目核心用途：照片初筛 |
| `photo-management` | 扫描、分组、批量移动/删除照片库 |
| `duplicate-detection` | `app/core/duplicates.py` 的多哈希相似组检测 |
| `image-quality` | `app/core/analyzer.py` 的质量评分与扣分规则 |
| `computer-vision` | 模糊度、边缘、姿态、遮挡等 CV 指标 |
| `opencv` | `opencv-python` 为主要依赖，`app/utils/image_utils.py` 基于 cv2 |
| `insightface` | 人脸检测、106 关键点、512 维特征聚类 |
| `paddleocr` | 中文 OCR，判定文字照片与截图质量 |
| `face-recognition` | 人物聚类与「人物一/人物二」分组浏览 |
| `live-photos` | `app/core/livephoto.py` 图片 + `.mov` 配对分析 |
| `video-analysis` | `app/core/video_analyzer.py` 抽帧与评分 |
| `desktop-application` | 桌面 GUI 程序，非 Web 服务 |
| `imagehash` | `imagehash` 提供 pHash / dHash / aHash |

> 注：`paddleocr`、`insightface`、`imagehash`、`onnxruntime` 等依赖仅存在于 `requirements.txt`（完整依赖）中，使用 `requirements-minimal.txt` 时对应的 OCR 与人脸功能会被禁用，但相关代码路径仍然存在，因此这些话题依然贴切。
