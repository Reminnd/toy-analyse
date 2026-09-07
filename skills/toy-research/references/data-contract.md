# 配置与报告数据

配置示例（不是用户已选择值）：

```json
{"country":"US","timezone":"Asia/Shanghai","daily_time":null,"engine":"python","sources":[{"platform":"amazon","list":"best_sellers","url":"<user-url>","target":200}]}
```

报告输入由 Codex 基于真实采集数据写入：

```json
{
  "title": "玩具选品日报", "country": "US", "collected_at": "ISO timestamp",
  "sources": [{"name":"Amazon Best Sellers","url":"https://...","target":200,"count":100,"note":"实际覆盖与缺口"}],
  "products": [{"id":"amazon:US:ASIN","platform":"amazon","product_id":"ASIN","title":"Observed title","rank":1,"source":"Amazon Best Sellers","url":"https://...","image_url":null,"image_scope":"product","brand":null,"listed_at":null,"rating":null,"review_count":null,"sales_day":null,"sales_week":null,"sales_month":null,"keywords":[],"missing_reason":"缺失原因"}],
  "reviews": [{"id":"review-id","product_id":"amazon:US:ASIN","text":"Actual review","rating":5,"date":null,"url":"https://..."}],
  "positive": [{"phrase":"易于组装","review_ids":["review-id"]}], "negative": [],
  "summary": "基于证据的观察与推断",
  "opportunities": [{"title":"建议","product_ids":["amazon:US:ASIN"],"reason":"依据与限制"}],
  "trends": [{"keyword":"toy","region":"US","window":"实际查询范围","value":null,"url":"https://..."}]
}
```

销量为 null 或 `{value,source,value_type,period_start,period_end,scope}`。类型区分平台展示、第三方估算和未知；scope 区分商品/父商品/SKU。保留实际窗口，rolling 30 days 不是自然月。自行聚合需同来源、同粒度且完整覆盖。28 天不补成 30 天。

同一商品可属于多个榜单，榜单独立计数，主表去重保留关联。跨平台以平台+国家+商品 ID 区分；相似标题不能合并销量。词云大小按主题引用的去重评论数，并输出样本分母；未取得评论时明确缺失。Google Trends 保留查询窗口、地区和词组，同批归一化指数才可比较。

多榜单商品使用 `sources` 保存榜单名称列表，`source_ranks` 保存各榜单的 `{source, rank}`，报告逐个显示排名。`rating_count` 是评分数量，`review_count` 是来源明确显示的文字评价数量；不能互相替代，已采集评论数量由 `reviews` 统计。
