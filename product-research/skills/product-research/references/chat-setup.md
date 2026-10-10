# 设置入口

## Codex：独立设置窗口

使用 SKILL.md 中的 scripts/setup.py 打开本机窗口。国家和大小类通过可滚动下拉选择，保存目录通过文件夹选择器选择。仅在 saved=true 后执行采集。已撤回聊天内原生长列表和分页选择流程。窗口与网页仍共用 settings.py 的范围校验及配置保存。

## ChatGPT 官方网页：HTML 组件

使用已连接 MCP 服务的 `product_research_settings` 工具显示 `ui://product-research/settings.html`。它提供 HTML select、optgroup、checkbox 和填写框，通过 MCP Apps 的 ui/initialize、tools/call、ui/message 连接聊天。大类列表首次按所选国家读取；每个大类的后续复合下拉同时包含自身和真实子类，支持继续细分。

不是把 HTML 代码贴进普通聊天，也不是发送本机文件链接就能嵌入。必须先把本包的 MCP 服务通过可访问的 HTTPS `/mcp` 地址接入 ChatGPT。未连接时如实说明缺少连接，不能宣称网页表单已在用户聊天中运行。开发、连接步骤见包根 README。

表单只保存用户提交的设置，然后向聊天发出继续执行消息。服务不创建自有 scheduler。若网页会话没有可用原生计划工具/本机执行器，明确记录“待落实”，不要把勾选或保存成功说成定时已启用。服务的工作目录不等于客户电脑目录；报告生成后由网页提供下载，用户通过浏览器保存到本机。

表单/国家页面失败时保留错误，使用正常浏览器检查并修复数据解析；不能编造选项。禁止把导出的会话/客户数据写入组件或 ZIP。

接口依据：[MCP Apps UI](https://developers.openai.com/plugins/build/chatgpt-ui)、[MCP server and UI quickstart](https://developers.openai.com/plugins/build/app-quickstart)。本地协议与浏览器测试不等于真实 ChatGPT 帐号连接验收。
