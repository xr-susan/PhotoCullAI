# PhotoCullAI

本地离线照片/视频废片自动筛选工具。

## 项目简介

PhotoCullAI 旨在帮助用户本地批量筛选照片和视频中的废片，支持模糊、闭眼、过曝、重复、相似、Live Photo 等多种检测策略。

## 项目结构

- `main.py`：应用入口
- `app/`：核心应用逻辑，包括分析器、UI、工具函数等
- `tests/`：pytest 单元测试
- `requirements.txt`：完整依赖
- `requirements-minimal.txt`：精简依赖，适合轻量部署
- `build_exe.bat`：打包 Windows 可执行文件
- `config.yaml`：默认配置
- `data/`：运行时缓存与报告目录
- `.gitignore`：忽略本地环境和生成文件

## 安装与运行

### 1. 创建虚拟环境

Windows PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows CMD:
```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 2. 安装完整依赖

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 运行程序

```powershell
python main.py
```

### 4. 精简版依赖（可选）

```powershell
pip install -r requirements-minimal.txt
```

> 精简版依赖适合无需完整机器学习功能的环境，但部分分析功能可能会受限。

## 开发与测试

```powershell
pip install -r requirements.txt
pip install pre-commit
pre-commit install
pre-commit run --all-files
pytest tests --maxfail=1 -q
```

## 打包 EXE

```bat
build_exe.bat
```

## 发布与变更日志

项目使用 `CHANGELOG.md` 跟踪版本变更，`GitHub Release` 模板用于创建正式发布说明。

发布流程：

1. 更新 `CHANGELOG.md`
2. 创建语义版本 tag，例如 `v1.0.0`
3. 推送 tag 到 GitHub：
   ```bash
git push origin v1.0.0
```

触发 `release` workflow 后，会自动生成 GitHub Release。

## 贡献与行为准则

欢迎贡献，但请遵循 `CONTRIBUTING.md` 和 `CODE_OF_CONDUCT.md` 中的规则。

## 使用建议

- 先备份原始照片
- 这是本地分析版，不会自动删除原图
- "移动到废片箱"只是移动，不是永久删除
- 大批量照片建议分批扫描
- 首次启动时 ML 模型会按需加载，无需等待

## 许可证

本项目使用 MIT 许可证。详见 `LICENSE` 文件。
