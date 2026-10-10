# macOS 安装与启动

适用于 Apple Silicon 与 Intel Mac；依赖安装需与本机架构一致，不复制 Windows 的 Python、node_modules 或会话文件。当前包已做代码适配，未在 macOS 实机验收。

## 安装

安装 Python 3.12+（推荐 python.org macOS 安装包，附带 Tkinter）、Node.js 20+ 和 Google Chrome。Python Tkinter 说明：[Python.org](https://www.python.org/download/mac/tcltk/)。Chrome 由 Playwright 的 chrome channel 查找，不使用 Windows 浏览器路径：[Playwright](https://playwright.dev/docs/browsers)。

将本包的 skills/product-research 文件夹复制到 `~/.codex/skills/product-research`，或自己设置的 CODEX_HOME 下的 skills 目录。在终端执行：

```sh
cd "${CODEX_HOME:-$HOME/.codex}/skills/product-research"
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
cd scripts
npm ci
../.venv/bin/python -m tkinter
```

最后一条应打开 Tk 测试窗口，确认后关闭。若报 `_tkinter` 缺失，应更换为带 Tk 的 Python 并重建虚拟环境；不要使用 pip 安装 tkinter。

## 在 Codex 启动

输入“启动 Product Research”。助手使用本 skill 目录的 `.venv/bin/python` 执行 `scripts/start.py`，工作目录取当前客户任务目录，参数分别传递以支持空格和中文路径。用户保存后自动采集，助手保持等待直到结果返回并继续分析、生成 HTML；取消窗口不执行采集。

设置窗口使用 macOS Aqua 控件、PingFang SC 中文字体和本机文件夹选择器。空白区域和说明区域支持鼠标/触控板滚动；下拉框内部由系统处理滚动。

遇到 Amazon 验证会打开可见 Chrome，用户手动验证后识别正常页面并保存本机会话，然后续采一次。关闭验证窗口则停止并保留已采数据。无需提供账号密码给助手。

## 桌面启动时找不到 Node

如果终端能运行 node，而桌面任务报找不到 node，在终端运行 `command -v node`，把返回的绝对路径设置为启动进程的 PRODUCT_RESEARCH_NODE 环境变量。例如由助手使用环境变量启动，不更改系统 PATH，也不要求将 Homebrew 安装到固定目录。

MCP 服务需要使用虚拟环境时，将 PRODUCT_RESEARCH_PYTHON 设为本 skill 的 `.venv/bin/python` 绝对路径。未设置时 macOS 使用 python3，Windows 使用 python。

## 本机验收

先确认设置窗口可显示中文、国家下拉和级联分类可选择，窗口和文件夹选择器可操作。然后保存一次不启用定时的配置，检查自动采集、手动验证续采、HTML 报告打开；取消设置应不启动采集。真实计划只在勾选启用后由 Codex 原生计划工具创建。
