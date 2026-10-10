# Product Research

客户初始化包支持 Amazon 国家与大小类选择、Codex 原生聊天选择与 ChatGPT MCP Apps 表单、可选 Codex 原生每日计划，以及可排序的 HTML 选品报告。国家与类目首次读取平台并缓存，后续由用户主动更新。包内不含个人账号、cookies、配置、历史报告或已启用计划。

- [下载客户初始化 ZIP](releases/product-research-client.zip)
- [客户安装与使用](product-research/README.md)
- [Product Research Skill](product-research/skills/product-research/SKILL.md)

下方保留早期玩具版本的说明和历史样例；新客户请使用上方 Product Research 包。

## 早期 toy-analyse

用于 Codex 的玩具选品 skill/plugin：配置国家、平台和榜单链接，优先使用 Python，必要时使用 Playwright，输出包含评论词云的 HTML/JSON 选品报告，并通过 Codex 原生 automation 定时执行。

## 使用与开发

- [安装和使用](INSTALL.md)
- [二次开发交接与未完成项](DEVELOPMENT.md)
- [配置示例](config.example.json)
- [Skill 入口](skills/toy-research/SKILL.md)
- [美国 Amazon 历史样例报告](samples/amazon-us-toy-report-2026-10-09.html)

```sh
cd skills/toy-research/scripts
python -m pip install -r requirements.txt
npm install
python -m unittest discover -s tests -p "test_*.py"
node --test tests/sales.test.mjs
```

浏览器脚本默认使用本机 Chrome。登录状态在本机工作目录保存，不提交 Cookie 或 API 密钥。定时任务由 Codex 创建，克隆仓库不会自动启动定时任务。

## 历史样例状态

两榜各100条，按ASIN去重后195个商品，保留5个缺口，不增加来源。2026-10-10补充194个详情，取得186个USD当前售价、69个参考价、192个商品图集，共1373个图片链接。榜单与20条语义分析评论样本沿用2026-10-09快照。

报告包含价格分布、品牌分布、当前售价与来源参考价对比、可筛选的中英文标题主题词云、好差评词云及可放大切换的当前ASIN图集。价格不是订单客单价；参考价缺失时不计算折扣。品牌数量不是市场份额，标题关键词不是搜索量。

美国 Amazon 为当前已验证平台。国家、链接、时间可配置；当前时间为 Asia/Shanghai 19:00，Codex 定时计划保持 PAUSED。其他平台与卖家API未完成真实账户接入。详情ASIN不一致的 B0FJ31ZCRB 保留列表信息，不合并其他变体详情。

[最新可视化报告](samples/amazon-us-toy-dashboard-2026-10-10.html) · [报告数据](samples/amazon-us-toy-dashboard-2026-10-10.json)
