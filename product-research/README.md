# Product Research · 客户初始化包

在 Codex 中选择 Amazon 国家和商品大小类，使用 Python 优先、Playwright 补充采集热销与新品榜单，并由 Codex 生成白橙配色的 HTML 选品分析报告。

## 安装

1. 解压本包。将 `skills/product-research` 文件夹复制到客户自己的 `$CODEX_HOME/skills/`；未自定义 CODEX_HOME 时通常为用户目录下的 `.codex/skills/`。
2. 在 Codex 新建或打开客户的本地任务目录。让 Codex 读取该 skill 并安装 `scripts/requirements.txt`；首次使用浏览器采集时，在 scripts 内执行 `npm ci`。
3. 输入 **启动 Product Research**。如当前任务未发现新 skill，重新打开 Codex 或新建任务后再试。

也提供标准 `.codex-plugin/plugin.json`，便于通过客户已有的本地插件发布流程安装。skill 复制安装和插件安装选择一种即可，避免重复载入。

环境：Python 3.12+（含 Tkinter）、Node.js 20+，浏览器路径使用 Chrome 或 Playwright Chromium。本版在 Windows 上验证；其他系统需要可用的 Tk 桌面环境。AI 分析使用当前 Codex，不附带独立 AI API。

## 首次和每次启动

打开本机设置窗口，选择国家、大类或下级类目；也可改两榜链接。国家/类目从 Amazon 获取并缓存，后来仅显式点击更新才刷新；未访问的下级类目首次展开时获取。国家站存在不代表它必定提供同样的榜单或所有指标。

勾选定时后填写 HH:MM 和 IANA 时区；保存后由 Codex 原生计划工具落实。未勾选时手动运行，安装不会自动启用计划。报告默认保存到当前任务 outputs，取消默认目录勾选后可浏览本机文件夹。设置窗口不会要求密码；采集实际需要登录时，Codex 才提示在正常浏览器处理。

报告含销量与评分排序、双语标题关键词/词云、品牌、商品价格分布、当前价和参考价对比、商品图集、好差评主题及来源证据。HTML 附同名 JSON 方便二次开发；图片从原站加载。

默认目标是两榜合计 200 个不重复商品；公开每榜上限及跨榜重复可能使实际数量不足，报告保留缺口。当前默认不追加其他类目凑数。已有脚本会补齐 Python 的可恢复遗漏，不将公开源范围不足描述为已达标。

## 初始化状态

包内没有客户国家/品类选择、计划、账号、API 密钥、cookies、浏览器档案、缓存、历史报告或本机路径。`config.example.json` 仅说明空配置，首次设置会在客户任务目录生成实际配置。不要将 `.auth`、浏览器 profile 或实际配置打包转发。

入口为 `skills/product-research/SKILL.md`。采集/会话说明见 `references/collection.md`，二次开发数据结构见 `references/data-contract.md`。目前仅提供 Amazon 原站实现；API 需要客户给出准确服务与文档后接入。
