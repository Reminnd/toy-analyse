# 卖家精灵 Python 接入

官方请求使用 `secret-key` header，脚本从用户指定环境变量读取，默认 `SELLERSPRITE_API_KEY`。不要把网页登录 Cookie 当作 API Key；两种权限需要分别验证。

## 选品数据与 200 条

```text
python scripts/sellersprite.py --output <work/products.json> products --marketplace <API-marketplace> --category <actual-node-path> --site-url <amazon-site-root>
```

`--category` 来自目标市场真实类目节点路径，不能用关键词随意代替。脚本请求该节点及下属分类，筛选大类 BSR 1–200，以原始 BSR 升序取去重 ASIN，最多 200 条。每页最多 100，最多遵循官方限制读取 2000 行；不足时保留缺口。需核对返回大类 `bsrId` 与用户目标类目一致，再将其称为该类目的第三方 BSR 候选。

这条路径可用于研究公开页面第 101–200 名之外的数据，但目前没有真实 API 凭证实跑，不能保证第三方库完整覆盖 200 个排名。第三方快照和官方当前榜单时间不一致时不得拼接成无来源的官方 Top 200。

`--new-releases` 按官方 API `badgeNR=Y` 筛选新品标识，再按大类 BSR 排序；它不是 Amazon 官方 New Releases 榜单。不能把大类排名称为新品榜排名。

`--month YYYYMM` 指定查询月份；不指定时保留 API 默认窗口未知。父体月销量 `units` 与子体近 30 日销量 `amzUnit` 分别保存，不能相加或互相替代。`sku` 字段是变体属性文本，不能当作已经验证的卖家 SKU 标识或 SKU 图片。

## 关键词趋势

```text
python scripts/sellersprite.py --output <work/trends.json> trends --marketplace <API-marketplace> --keyword <keyword>
```

调用卖家精灵 Google Trends 代理接口，保留实际查询链接与时间序列；不是直接 Google 官方 API。返回市场或关键词不匹配时拒绝结果。不把独立查询的归一化指数直接混排。

## 评论

```text
python scripts/sellersprite.py --output <work/reviews-page1.json> reviews --marketplace <API-marketplace> --asin <asin> --page 1
```

每页最多 10 条，保存平台原始响应。官方文档未给出完整响应封装示例，因此在首次真实调用后确认结构和评论身份，再转换为报告格式。不要根据数组位置伪造平台评论 ID。

官方依据：[产品研究](https://open.sellersprite.com/api/2)、[Google Trends](https://open.sellersprite.com/api/12)、[查评论](https://open.sellersprite.com/api/25)、[排序字段](https://sellersprite.github.io/#table-16-product-research-and-competitor-lookup-sorting-fields)。
