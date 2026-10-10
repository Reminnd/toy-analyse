# 聊天内设置

## Codex：原生选择与填写

检测当前会话实际可用的用户输入工具。优先使用 `request_user_input_async` 的 options 展示国家/类目选择，省略 options 提供文本填写；若只有 `request_user_input` 则遵循其当前模式和 schema 的限制，不强行在不支持的模式调用。没有原生输入工具时才直接在聊天中询问。不要启动 Tkinter、独立浏览器表单或终端问答代替 Codex 聊天。

原生工具不是 HTML select，不能声称已经实现自定义下拉组件；使用宿主实际渲染的选项卡/文本回答。按依赖顺序分步显示：

1. 显示“平台：Amazon”。读取 markets 的实际选项，用国家名称及 country code 构造 options。列表过长时按宿主支持的数量分页，提供“下一组选项”，不能隐藏未列国家或伪造选项。用户可直接填已返回的国家名称或代码。
2. 用户选国家后首次调用 categories（category_keys=[]），加载该市场大类。展示大类选项；国家改变时清除已选类目和旧链接。
3. 选大类后 categories(category_keys=[大类key]) 返回的 choices 包含大类自身 `is_self=true` 和实际直接子类。自身标签使用“类目名称（该类自身）”，不能只有子类而漏掉大类。用户选子类后继续加载它自身和下级，直到选自身或已无下级；不要用父节点自动代替用户已选子节点。
4. 原生选择是否启用每日计划；启用时填写 HH:MM 和时区。输入保存目录（可选默认 outputs），根据宿主实际可用的文件保存/选择工具展示目录选择；无该工具时使用文本框，不虚构按钮。已有回答可预填，但启动设置不代表用户授权默认提交。
5. 将用户回答写为工作目录中的 draft-settings.json，调用 save；后台校验成功才算保存。随后调用 plan，使用返回来源启动采集，并按 schedule_enabled 处理原生计划。无需再询问同一项是否确定。

命令（输入文件 `{}` 可用于首次 markets；不要依赖交互式 stdin）：

```text
python scripts/settings.py --workspace <workspace> --action markets --input <empty.json>
python scripts/settings.py --workspace <workspace> --action categories --input <selection.json>
python scripts/settings.py --workspace <workspace> --action save --input <draft-settings.json>
python scripts/settings.py --workspace <workspace> --action plan --input <empty.json>
```

selection.json 为 `{"country":"<observed country code>","category_keys":["<observed parent key>"]}`，根类目使用空数组。显式更新时传 `refresh:true`；未提供时缓存存在则不刷新。第一次访问一个节点会读取该节点下级，不一次递归抓取整站。返回 source/fetched_at 可用来说明选项来源。

draft-settings.json 使用 country、category_keys、schedule_enabled（布尔值）、time、timezone、output_directory（null 为默认，路径为运行环境中的目录），可选 custom_sources（依序热销榜/新品榜两个 URL）。custom_sources 必须匹配所选国家及最终类目；若用户确实要换类目，先更新选择，不沿用旧链接。

## ChatGPT 官方网页：HTML 组件

使用已连接 MCP 服务的 `product_research_settings` 工具显示 `ui://product-research/settings.html`。它提供 HTML select、optgroup、checkbox 和填写框，通过 MCP Apps 的 ui/initialize、tools/call、ui/message 连接聊天。大类列表首次按所选国家读取；每个大类的后续复合下拉同时包含自身和真实子类，支持继续细分。

不是把 HTML 代码贴进普通聊天，也不是发送本机文件链接就能嵌入。必须先把本包的 MCP 服务通过可访问的 HTTPS `/mcp` 地址接入 ChatGPT。未连接时如实说明缺少连接，不能宣称网页表单已在用户聊天中运行。开发、连接步骤见包根 README。

表单只保存用户提交的设置，然后向聊天发出继续执行消息。服务不创建自有 scheduler。若网页会话没有可用原生计划工具/本机执行器，明确记录“待落实”，不要把勾选或保存成功说成定时已启用。服务的工作目录不等于客户电脑目录；报告生成后由网页提供下载，用户通过浏览器保存到本机。

表单/国家页面失败时保留错误，使用正常浏览器检查并修复数据解析；不能编造选项。禁止把导出的会话/客户数据写入组件或 ZIP。

接口依据：[MCP Apps UI](https://developers.openai.com/plugins/build/chatgpt-ui)、[MCP server and UI quickstart](https://developers.openai.com/plugins/build/app-quickstart)。本地协议与浏览器测试不等于真实 ChatGPT 帐号连接验收。
