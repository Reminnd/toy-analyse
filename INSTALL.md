# 在 Codex 中使用

本交付包含一个标准插件包和其中的 `toy-research` skill。当前采用个人 skill 安装方式；没有注册独立 Web 应用或后台调度器。

在新建 Codex 任务中选择 GPT-5.6 Terra，然后输入：

```text
使用 $toy-research，先让我选择目标国家和平台，再配置每日选品报告。
```

也可直接给定国家、平台、链接和每天时间。skill 会使用 Codex 原生计划工具；安装时不会擅自开启默认时间的采集。报告以 Codex 任务文件提供，使用原生文件操作保存或导出。

Python 优先，Playwright 备用，两个程序均保留。Python 使用 Requests、BeautifulSoup，参考 Scrapy 的有限重试和分页处理；两条路径都记录实际结果，不补造 200 条。详细来源与 GitHub 参考见 skill 的 `references/sources.md`。

当前 Python 已通过内嵌商品清单从 60 条补齐到 Amazon 公开排名 1–100，并验证了一个商品的品牌、平台购买量文案与 13 条可见评论。已加入登录状态保存/复用与缺口诊断。Temu、TikTok Shop、AliExpress 仅有公共结构化数据初始解析；Temu 与 AliExpress 实际探测分别需要浏览器校验与登录。卖家精灵新增 Python 分页选品、Google Trends 代理查询与评论接口，FastMoss 附官方搜索和日销量历史脚本；这些 API 尚未用真实凭证验证。全部平台字段适配与完整 200 条仍需目标市场实跑。“选品助手”需提供准确网址。

报告支持基于真实评论的好差评词云；当前新版验证报告包含单个商品的评论样本与有限选品分析，不代表完整 200 条日报。Terra 已按分批读取与脚本执行设计，尚未做该模型的独立端到端实跑。
