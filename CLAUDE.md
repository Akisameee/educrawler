## 环境管理要求
- **严禁使用 pip**：在本项目中，禁止直接运行 `pip install` 命令。
- **强制使用 uv**：所有依赖管理、环境创建和脚本运行必须通过 `uv` 完成。
- **避免全局污染**：确保所有依赖都安装在项目本地的虚拟环境（.venv）中。

## 常用操作指令
- **创建环境**：`uv venv`
- **激活环境**：`source .venv/bin/activate`
- **添加依赖**：`uv add <package_name>`
- **删除依赖**：`uv remove <package_name>`
- **同步环境**：`uv sync`
- **运行脚本**：使用 `uv run <script.py>` 自动在虚拟环境中执行。

## 环境初始化与迁移 (从 requirements.txt)
当项目中存在旧的 `requirements.txt` 时，请按以下步骤构建 `uv` 环境：
1. **初始化项目**：`uv init` (如果还没有 pyproject.toml)。
2. **导入依赖**：使用 `uv add -r requirements.txt` 将所有旧依赖批量添加到 `pyproject.toml`。
3. **锁定环境**：运行 `uv lock` 生成 `uv.lock`。
4. **同步安装**：运行 `uv sync` 创建并同步 `.venv` 虚拟环境。
5. **清理旧文件**：转换成功后，建议删除 `requirements.txt` 以保持项目整洁。

## 开发约定
1. **提交规范**：不要提交 `.venv` 文件夹，但必须提交 `uv.lock` 文件以确保环境可复现。
2. **代码运行**：在建议运行代码时，请始终提供以 `uv run` 开头的命令。
3. **更新文档**：当你进行了任何修改后，请同步 `SPEC.md` ，包括实现的功能，未解决的bug或者TODOs。

## 报错处理
如果发现环境损坏，请直接执行 `rm -rf .venv && uv venv && uv sync` 进行重置。

## 敏感信息保护
1. .yml, .yaml的文件在填入信息之后都是禁止打开的