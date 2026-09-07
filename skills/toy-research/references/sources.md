# 来源接入

## GitHub 成熟方案借鉴

参考 [Scrapy](https://github.com/scrapy/scrapy) 的解析与下载分离、[RetryMiddleware](https://github.com/scrapy/scrapy/blob/master/scrapy/downloadermiddlewares/retry.py) 的有限临时失败重试，以及 [Requests](https://github.com/psf/requests) 的 Session 连接复用。当前 Python 程序使用 Requests + BeautifulSoup：重试最多两次，仅处理 GET 的 429/500/502/503/504，不重复尝试 401/403。分页跟随实际 next 链接、商品按 ID 去重，避免猜测分页 URL。

参考 [scrapy-playwright](https://github.com/scrapy-plugins/scrapy-playwright) 的动态页面处理与浏览器资源生命周期，当前独立 Playwright 程序在 finally 中关闭上下文。没有复制这些项目的源码，也不宣称已经集成完整 Scrapy 框架；选择此规模是为了在 Codex 单次任务中运行两个独立采集方案。

- Amazon：[玩具热销榜](https://www.amazon.com/Best-Sellers-Toys-Games/zgbs/toys-and-games)、[玩具新品榜](https://www.amazon.com/gp/new-releases/toys-and-games)。2026-09-07 Python 已读取内嵌清单并补齐热销榜 #1–#100，无声明排名缺口；页面自动配送到日本，实际市场需重验。来源没有提供 #101–#200。
- FastMoss：[商品搜索](https://developers.fastmoss.com/zh/api/docs/product/v1/search.html)、[日销量](https://developer.fastmoss.com/api/docs/product/v1/salesTrend.html)。Bearer token、region、类目 ID 需正确。近 7 日销量降序是第三方排序，`is_new_listed` 是平台新品定义；均不冒充 TikTok 官方榜单。日趋势单次 1–28 天，月窗口需历史积累。
- 卖家精灵：[产品研究 API](https://open.sellersprite.com/api/2)。鉴权、字段与配额按当前账号验证，付费账号不自动意味着 API 权限。

选择卖家精灵时读取 [sellersprite.md](sellersprite.md)，使用 Python 脚本请求分页选品、Google Trends 代理数据或评论。已按官方文档实现请求和已公开字段解析，真实账户权限与完整数据覆盖尚未验证。
- AliExpress：[Affiliate Product Query](https://developer.alibaba.com/docs/api.htm?apiId=45803)。验证联盟覆盖及排序，不等同全站 Top 200。
- Temu：[Partner Platform](https://partner.temu.com/)。卖家管理权限不等于全市场竞品数据权限。
- Google Trends：[数据定义](https://support.google.com/trends/answer/4365533?hl=en)。通过浏览器导出实际查询或用已开通 API。Trending Now 新闻热点不能替代玩具关键词研究。

先验证一次目标市场、明确类目或商品的 API 请求，再扩大。仅用用户指定的凭证或已连接工具，不扫描机器找密钥。源错误记录为错误，不能写成商品。

原站保留 Playwright 与 Python。内置脚本解析 Amazon 榜单及公共 JSON-LD Product；Temu、TikTok Shop、AliExpress 标记可能不覆盖列表，需验证并按当前页面适配。详情、评论不可用时保留字段与样本缺失。

2026-09-07 原站探测：Temu 加拿大玩具搜索链接返回 HTTP 200 浏览器校验页；AliExpress 玩具类目返回 HTTP 200 登录跳转页。Python 分别输出 `browser_challenge` 与 `login_required`，不能将它们当作空榜单或已有数据支持。需在用户有效会话下继续验证。

200 条不足时找同市场、同类目、同排名定义的来源。没有可用来源则明确交付部分结果，200 条要求仍未完成，不悄悄降为 100。

FastMoss 也提供独立脚本，凭证从用户指定环境变量读取：

```text
node scripts/fastmoss.mjs --country <country> --category <actual-category-id> --list best_sellers --output <work/fastmoss.json> --key-env FASTMOSS_API_KEY
```
