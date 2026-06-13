# PhotoCullAI

本地离线照片/视频废片自动筛选工具。

## 功能
- 图片废片分析：模糊、闭眼、姿势、曝光、文字清晰度、歪斜、反光
- 景色分析：模糊、曝光、歪斜、色彩平淡、主体不足
- 视频分析：关键帧模糊、过曝、欠曝、过短
- Live Photo 支持：HEIC + MOV
- 重复/相似图检测（感知哈希 + 文件大小）
- 人脸特征聚类，按人物分组
- 氛围感照片智能识别（柔焦/暖调/暗调不误判）
- 拖拽导入
- 左侧目录树筛选
- 右侧缩略图网格（异步加载）
- 批量保留 / 移动废片箱 / 永久删除
- 一键选择废片 / 一键保留最佳
- 预览 + 人工确认（缩放/旋转/平移）
- 导出 CSV / JSON 报告
- 本地运行，不依赖云服务

## 安装
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 精简版安装（不含大型 ML 库，功能受限）
```bash
pip install -r requirements-minimal.txt
```

## 打包 EXE

```bat
build_exe.bat
```

## 说明

* 先备份原始照片
* 这是本地分析版，不会自动删除原图
* "移动到废片箱"只是移动，不是永久删除
* 大批量照片建议分批扫描
* 首次启动时 ML 模型会按需加载，无需等待

## 许可证

本项目使用 MIT 许可证。详见 `LICENSE` 文件。
