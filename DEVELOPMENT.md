# 二次开发交接

本包为当前实现快照，不表示完整目标已实现。入口为 `skills/toy-research/SKILL.md`，Python、Playwright、API 客户端和 HTML/JSON 报告渲染器位于其 `scripts/` 目录。

## 环境与执行

在 `skills/toy-research/scripts/` 中执行：

```sh
python -m pip install -r requirements.txt
npm install
python -m unittest discover -s tests -p "test_*.py"
node --test tests/sales.test.mjs
```

浏览器脚本默认使用本机 Chrome；实际参数见脚本 `--help` 或 `parseArgs` 定义。安装和配置说明见 `INSTALL.md`。无需独立网站、额外 AI API 或自建调度服务；分析由 Codex 执行，定时任务使用原生 automation。

## 已验证

- 美国 Amazon 配送基准为 New York ZIP 10001。浏览器保存的匿名 `storageState` Cookie 可被 Requests 复用，两个榜单实测保持该配送地区。
- 热销榜 Python 取得排名 1–100；新品榜 Python 取得 99 条，另用浏览器原始商品卡片补齐第32名。合计200条榜单记录、193个去重商品，不是每榜200条。
- 本轮保存1,108条去重可见评论，报告对20个商品的36条定向评论样本进行语义分析，生成好差评词云。评论可能跨国家、时间和变体。
- 报告支持多榜单独立排名、评分数与文字评价数分离、缺失字段及证据引用校验。
- 已修复明确的 `Brand:` 页首品牌、`#acrPopover` 评分解析，并识别 HTTP 200 的 `Continue shopping` 验证页。5项 Python 测试和浏览器真实结构片段验证通过。

## 下一步开发重点

1. **折叠详情表适配尚未完成。** 浏览器实测 `B0G36VXNGX`，展开 `Item details` 后可见 `Brand Name: Horizon Group USA`。现有表格选择器及品牌标签未覆盖这一结构。需要检查真实容器与加载方式，再同步 Python/Playwright 解析；不要凭猜测补字段。读取其 HTML 的后续操作因工具自动审批用量上限中断。
2. **浏览器定向补采尚未集成为通用流程。** 本次新品第32名为人工编排的浏览器补采；源码中常规浏览器采集器尚不能自动消费 Python 的缺口列表。应按原ASIN和原榜单排名补采，不能把详情页切换后的另一变体指标合并进来。
3. **每榜200条未达到。** 当前公开榜单仅声明1–100名；需确认同市场、同类目、同排名口径的其他来源，不能用子类目拼成全类目Top 200。
4. **指标仍不完整。** 精确日周月销量、上架时间、完整SKU图片均未取得；品牌仍有缺失。部分详情请求返回验证页。不要把月购买提示换算成精确销量。
5. **其他平台接入未完成。** Temu、AliExpress需要有效会话；TikTok Shop只有初始网页解析。SellerSprite、FastMoss官方API客户端已实现，但用户明确尚未配置API，未经真实账户联调。Google Trends代理接口亦未实跑；选品助手网址暂定。
6. **Terra尚未独立端到端验证。** 当前采用每批不超过40个商品、确定性脚本与简短状态的设计，不能声称已完成Terra适配验证。

## 配置与敏感文件

`config.example.json` 提供美国Amazon、每天19:00、Asia/Shanghai的示例。修改并保存为任务目录的 `toy-research.config.json`。在新机器上重新保存会话，把本机路径填入 `storage_state`。

包内不包含 Cookie、API密钥、浏览器配置目录、node_modules 或原始完整评论。会话文件只保存在工作目录，不进入插件或报告。

原机器已创建名称为“美国 Amazon 玩具选品日报”的原生定时任务，ID为 `amazon`。它保存在 Codex 中，不随ZIP迁移；本次打包没有修改其状态。在新机器上应通过 Codex 原生工具重新配置，不自行启动后台服务。

`samples/` 是已交付报告和短评论摘录，可用于了解数据契约，不应作为新一次采集的数据来源。
