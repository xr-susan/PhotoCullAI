# Contributing to PhotoCullAI

感谢你对 PhotoCullAI 的关注！欢迎通过以下方式贡献代码、文档和测试。

## 贡献方式

1. Fork 本仓库
2. 创建 feature 分支：
   ```bash
git checkout -b feature/your-feature-name
```
3. 提交修改：
   ```bash
git add .
git commit -m "Add feature X"
```
4. 推送到你的远程仓库：
   ```bash
git push origin feature/your-feature-name
```
5. 提交 Pull Request

## 提交规范

- 使用简洁明了的提交信息
- 代码应保持可读性，遵循现有项目风格
- 对新增功能或修复的代码尽量补充测试
- 避免提交本地生成文件和环境目录

## 开发流程

- 新功能使用 `feature/` 前缀
- Bug 修复使用 `fix/` 前缀
- 文档修改使用 `docs/` 前缀

## 本地测试

推荐使用 pytest 进行本地测试：

```bash
pip install -r requirements.txt
pip install pre-commit
pre-commit install
pre-commit run --all-files
pytest tests --maxfail=1 -q
```

## 发布流程

为了创建正式发布，请使用语义版本 tag，例如：

```bash
git tag v1.0.0
git push origin v1.0.0
```

这将触发 GitHub Release workflow，并根据 `CHANGELOG.md` 生成发布说明。

## 报告问题

如果你发现 bug 或希望新增功能，请在仓库 Issues 中提交请求，并尽可能提供重现步骤。

## 代码风格

本项目使用 Python 编写，建议遵循以下基本风格：

- 使用 4 个空格缩进
- 使用有意义的变量名
- 保持函数职责单一
- 添加必要的注释和 docstring
