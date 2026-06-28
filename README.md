# PhotoCullAI

PhotoCullAI 是一个本地运行的照片和视频初筛工具。它不会上传文件，也不会自动删除原图；它做的事情很明确：扫描一批媒体文件，给出保留、待复核、废片建议，并把结果导出成报告。

它适合先粗筛旅行照、活动照、截图、Live Photo 和短视频，再由人做最后确认。

## 功能

- 扫描文件夹或手动选择照片/视频
- 识别常见问题：模糊、曝光异常、闭眼、文字照片倾斜、截图质量差等
- 标记相似照片组，并推荐每组保留分数最高的一张
- 支持 Live Photo 配对分析
- 按目录、人物和相似组浏览结果
- 批量保留、移动到废片箱、永久删除
- 导出 CSV、JSON 和筛选摘要

## 报告输出

点击“导出报告”后会生成：

- `data/reports/photo_cull_report.csv`：适合 Excel 查看
- `data/reports/photo_cull_report.json`：完整逐项结果
- `data/reports/photo_cull_summary.json`：总数、废片数、相似组、预计可释放空间等摘要

## 安装

建议使用虚拟环境：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

启动：

```powershell
python main.py
```

如果只想运行基础功能，可以尝试精简依赖：

```powershell
python -m pip install -r requirements-minimal.txt
```

精简依赖下，部分人脸、OCR 或视频分析能力可能不可用。

## 使用建议

- 第一次处理重要照片前，先用少量样本试跑
- 批量删除前先看“待复核”和“相似组”
- “移动到废片箱”只是移动到项目的 `data/junk` 目录，不等于系统回收站
- 永久删除不可恢复，建议确认备份后再使用
- 大批量照片可以按文件夹分批扫描，界面会更顺畅

## 项目结构

```text
PhotoCullAI/
  main.py                 应用入口
  app/core/               分析、重复组、Live Photo、摘要统计
  app/ui/                 PyQt6 桌面界面
  app/utils/              文件、配置、图像工具
  tests/                  单元测试
  config.yaml             默认阈值和路径配置
```

## 测试

```powershell
python -m pytest tests -q
```

## 打包

```bat
build_exe.bat
```

## 许可证

MIT
