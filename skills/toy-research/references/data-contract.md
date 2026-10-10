# 配置与报告数据

数量口径：配置与报告顶层 `unique_product_target=200`，表示合计 200 个不重复商品。同一 Amazon 市场按 ASIN 去重，商品 id 使用 `amazon:US:ASIN`，保留各榜单来源和排名。单来源 target 为采集上限，当前两榜各 100；报告分别展示来源覆盖与合并后实际数量、缺口。当前用户明确不启用补充来源：`supplemental_sources_allowed=false`、`shortfall_policy="report"`。仅采现有两榜并保留缺口，不能为达到200而加入子类目。声明的ASIN数与已取得标题的有效商品数必须区分。

详情主图在页面 `input#ASIN` 与榜单 ASIN 一致时，记录 `image_scope="selected_asin"`、`image_asin` 及 `image_url`，报告必须保留并显示该关联。未取得明确 ASIN 时仍标为 `product`。这表示当前选中 ASIN 的主图，不表示已取得卖家内部 SKU 编号或全部变体图片。

2026-10-09 当前目标更新：仅启用 Amazon；销量使用 `displayed_sales_message` 的来源原文，报告不要求拆分日周月销量。关键词使用 `keywords: [{"en":"latex balloons","zh":"乳胶气球"}]`；由 Codex 根据真实页面内容提取并翻译。下方历史样例中的日周月指标和上架时间不再是本轮必填目标，历史数据仍可读取。

配置示例（不是用户已选择值）：

```json
{"country":"US","timezone":"Asia/Shanghai","daily_time":null,"engine":"python","unique_product_target":200,"sources":[{"platform":"amazon","list":"best_sellers","url":"<user-url>","target":100}]}
```

报告输入由 Codex 基于真实采集数据写入：

```json
{
  "unique_product_target": 200, "title": "玩具选品日报", "country": "US", "collected_at": "ISO timestamp",
  "sources": [{"name":"Amazon Best Sellers","url":"https://...","target":100,"count":100,"note":"实际覆盖与缺口"}],
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

## 详情补充字段

`pricing` 包含 `current_price`、`reference_price`、`currency`、`currency_symbol`、`reference_label`、`source`、`discount_percent`。未观察到的值为null；参考价未必是原价，以原标签为准。当前售价不能直接称活动价。仅参考价大于当前价时计算 `(reference_price-current_price)/reference_price*100`。USD价格分布只统计USD样本，不跨币种混算，不将单价解释为订单客单价。

`gallery` 是 `{url,image_role,asin,scope:"selected_asin",source}` 数组，`image_role` 为 MAIN/PT01 等图片位置。只接受当前详情ASIN及主图资产匹配的图集，缺失时为空数组；不代表卖家内部SKU或全部变体。`gallery_status` 为 embedded_initial 或 not_observed。报告可保存 `expanded_at`，区分详情刷新时间与榜单原始时间。

两种详情解析器返回 `attributes`（原字段名与原单位）及 `feature_bullets`（About this item 原文，仅作为分析输入）。报告商品可以包含 `specifications: {"Material":"Clay","Manufacturer recommended age":"3 years and up"}` 和 `feature_summary`（Codex基于实际详情写的简短中文概述）。渲染器在商品行提供展开区。只写页面明确提供的规格；商品文案不作为已证实效果，公开报告使用简要概述而非复制完整营销段落。
