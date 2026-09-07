# Python 优先采集与登录状态

## 可保存的状态

保存浏览器 `storageState`，不是截图、DOM 快照或 HTML。状态包含 Cookie、localStorage，并可包含 IndexedDB。Python Requests 只会使用导入的 Cookie；它不会执行 localStorage 或 IndexedDB 中的应用逻辑，也不能用文件替代过期会话或动态浏览器校验。

用户在交互终端启动一次登录浏览器，完成登录和配送地区设置后按 Enter 保存：

```text
node scripts/save_session.mjs --url <platform-url> --output <work/.auth/platform-country.json>
python scripts/python_crawler.py --platform amazon --country <country> --url <list-url> --storage-state <work/.auth/platform-country.json> --details --output <work/raw.json>
```

只让用户在网站中输入密码，不让用户在对话中发送密码。快照含会话凭证，不放入 `outputs/`、插件包或报告。加载器跳过过期和无关域 Cookie，保留 domain/path/secure/expires；加载数量不代表登录有效。用实际目标页面验证，若返回登录或访问限制则标记需要更新状态。

浏览器备选也可复用同一状态：

```text
node scripts/playwright_crawler.mjs --platform amazon --country <country> --url <list-url> --storage-state <work/.auth/platform-country.json> --profile <work/browser-profile> --details --output <work/browser.json>
```

## 数量缺失的处理顺序

1. 核对配置市场、榜单 URL、实际分页和去重 ID，先排除配置错误。
2. 检查 HTML 中的结构化数据。Amazon 当前 `data-client-recs-list` 包含未渲染商品 ID 和 `render.zg.rank`；程序读取真实清单，并请求缺少标题的商品详情。只有取得标题才计入完整商品，失败项保存在 `unresolved_products`。
3. 跟随页面实际 next 链接。某一页失败时保留之前的结果和 `pagination_error`；不能把未读完的分页认定为榜单只有这么多条。
4. 查看 `coverage.missing_declared_ranks`：这是页面声明存在但尚未取得的商品。只针对这些缺口重试或使用浏览器补采，不重复整轮扫描已完成商品。
5. `source_range_shortfall=true` 表示已读完该来源且声明范围不足目标。不能通过重试制造第 101–200 名，需有相同市场、类目和排名口径的其他数据源；仍不足就明确交付部分报告。
6. HTML 不提供数据时，检查浏览器实际网络请求，验证可在同一用户会话中使用的商品接口及分页参数；不要凭猜测拼接接口。只有接口需要动态浏览器状态时才维持 Playwright 备选。

## 已验证的接入边界（2026-09-07）

- Amazon 地区会话复用已实测：在公开浏览器的配送设置中使用美国 ZIP `10001`，保存匿名 `storageState` 后，Requests 分别请求热销榜和新品榜，两个页面均显示 `Deliver to New York 10001`。该证据证明本次配送 Cookie 可复用，不证明用户账户已登录，也不保证会话永久有效。配置记录实际邮编，每轮重新核对页面。
- 新品榜未设置美国配送状态的初次探测取得 99 条，声明排名 1–100。第 32 名 ASIN `B0H7PRJVD9` 的详情显示另一变体 `B0H7PWTPTV`，保留缺口，不把另一变体字段填入原商品。该旧探测的配送地区为 Japan，不作为美国完整榜单交付。

- Amazon 本次公开榜单共取得 100 条真实商品，排名 1–100 无缺口；该来源未提供第 101–200 名。实际配送地区为 Japan，不能作为其他市场已验证的完整 Top 200。
- Temu 加拿大玩具分类链接在 Requests 中返回 JavaScript challenge；正常浏览器加载后跳转到 `login.html`，页面标题为 `Temu | Login`。本次未取得商品，必须先由用户完成登录，再验证保存状态能否供 Requests 复用。此链接是分类页，不能自动认定为 Best Sellers 榜单。
- AliExpress 本次公开分类页在 Requests 中返回登录跳转内容，尚未取得商品。
- SellerSprite 与 FastMoss 已实现官方 API 客户端，但没有实际凭证联调结果；接口实现和离线测试不代表已取得数据。

上述阻塞出现后应明确请求所需的登录状态或 API 接入，不反复请求同一个未登录页面，不将空列表当作采集成功。

## 详情与销量说明

Python 与 Playwright 均解析详情页明确的 `#bylineInfo` 中 `Brand:` 品牌和 `#acrPopover` 汇总评分。不能把 `Visit the … Store` 商店名直接当作品牌。2026-09-07 使用真实 HTML 片段验证两种解析结果一致；ASIN 与榜单不一致时仍拒绝合并详情。

Amazon `HTTP 200` 也可能是 `Continue shopping` 验证页。实际返回的表单路径包含 `/errors_page/validateCaptcha`；详情解析器将其明确报告为验证页面，不作为空商品或品牌缺失的有效详情。不要循环重试该页面；需要在浏览器完成正常验证后再检查会话是否可复用。

`--details` 补充 Amazon 公开详情与页面可见评论，不表示已下载全部评论。上架日期只有源页面明确提供才填写；`#acrCustomerReviewText` 的数值保留为评分数量 `rating_count`，不能当作已采集评论数量。月购买量提示保留 `displayed_sales_message`，不换算成精确销量。

FastMoss 需要已授权凭证；`--sales-history <work/history> --end-date YYYY-MM-DD` 在搜索后拉取近 28 日日销量并按市场/商品积累。重复日期更新，不重复累加；只有历史完整覆盖 30 天才输出月窗口总和。首次 28 天不足时月销量 null。接口时区未说明时保留未知，不擅自称为目标市场昨日。

参考：[Playwright Authentication](https://playwright.dev/docs/auth)、[Requests Session](https://requests.readthedocs.io/en/latest/user/advanced/#session-objects)。
