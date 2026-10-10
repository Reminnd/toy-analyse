# Product Research · 客户初始化包

Amazon 国家与大小类选择、Python 优先 / Playwright 补充采集，以及含销量/评分排序、双语关键词、价格、品牌、图集和好差评词云的 HTML 报告。

## Codex 安装与启动

把 `skills/product-research` 复制到客户自己的 `$CODEX_HOME/skills/`（默认用户目录 `.codex/skills/`），安装 scripts/requirements.txt 依赖，在 Codex 中输入 **启动 Product Research**。未发现新 skill 时重新打开任务或 Codex。不要同时装两份同名 skill。

启动时打开本机独立设置窗口，提供可滚动国家下拉框、大小类级联下拉框、定时填写和文件夹选择器。保存后继续采集；取消不启动。国家和品类从 Amazon 读取并缓存，每次显式启动均可修改；自动任务读取已保存配置。

环境：Python 3.12+（含 Tkinter）、Node.js 20+；需要浏览器或 ChatGPT 组件时，在 scripts 目录运行 `npm ci`。浏览器采集默认 Chrome，也可使用 Playwright Chromium。

## ChatGPT 官方网页内嵌设置

包内包含 MCP Apps HTML 表单和 MCP 服务。真正嵌入官方聊天需要先连接该服务，仅上传 ZIP 或 HTML 文件不会自动启用组件。

在安装依赖后，从 scripts 目录运行（使用客户自己的工作目录）：

```text
python -m pip install -r requirements.txt
npm ci
node chat_server.mjs --http --workspace <customer-workspace> --port 8787
```

服务监听 `127.0.0.1:8787/mcp`。如 Python 命令不是 python，设置 `PRODUCT_RESEARCH_PYTHON` 为可执行文件路径。也可省略 --http，使用标准输入输出 MCP transport 连接本机宿主。

通过客户自己的 HTTPS 反向代理或开发隧道暴露 `/mcp`，在有相应权限的 ChatGPT 开发者连接中添加地址。此服务按单客户工作目录设计，不作为共享多租户服务发布。包内没有预设公网地址，也不会自动开启隧道或发布服务。

连接后调用 `product_research_settings`：聊天显示 HTML 国家/大类 select；每级复合下拉使用 optgroup，包含该类自身和直接子类。提交通过工具校验并写入配置，再通知聊天助手继续采集。网页原生计划、执行环境和下载能力仍取决于当前宿主；保存成功不代表定时计划已创建。网页的报告本机位置由下载时的浏览器保存操作决定。

## 范围与采集

国家选择绑定实际 Amazon 域名；类目选择绑定该国家分类树的实际 key 和来源 URL。首次选国家读取大类，首次选大类读取其子类；以后只有显式更新才刷新缓存。选大类自身就采该大类，选小类就采小类，不把子类请求替换成大类。切换国家清空旧类目。

统一入口校验配置后执行：

```text
python collect.py --workspace <workspace> --source best_sellers --output <work/best.json>
python collect.py --workspace <workspace> --source new_releases --output <work/new.json>
```

浏览器补采增加 `--engine playwright`，需要定向恢复时再加 `--python-result <raw.json>`。两套爬虫核对实际页面的国家域名与类目；错误跳转不计为选定范围的数据。自定义榜单 URL 必须匹配所选站点、类目和榜单类型。

默认两榜合计目标 200 个不重复商品；公开范围和跨榜重复可能导致不足，报告保留缺口，不添加未授权来源。原站先公开访问，实际需要登录时才提示，快照只留客户本机。API 需客户提供准确服务和文档后接入。

## 二次开发与初始化状态

入口 `skills/product-research/SKILL.md`；聊天流程 `references/chat-setup.md`；采集与会话 `references/collection.md`；研究结构 `references/data-contract.md`。客户包不含个人配置、账号、cookies、运行缓存、历史报告和已启用计划，config.example.json 为空配置。

在 scripts 内执行 `python -m unittest discover -s tests` 和 `node --test tests/chat.test.mjs` 验证代码。真实 ChatGPT 连接需要客户自己的可用 HTTPS 地址及账号；本地测试不替代线上验收。
