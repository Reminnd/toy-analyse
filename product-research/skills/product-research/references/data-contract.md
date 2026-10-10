# 配置与研究 JSON

聊天表单提交后创建 `product-research.config.json`：platform、country、marketplace、category_path、sources、engine、unique_product_target、schedule_enabled、time、timezone、output_directory、format。category_path 的每项保留 Amazon 原始 label、url 和 key。sources 为 `{name,list,url,target}` 数组，target 是单来源采集上限。可按实际需要添加 storage_state 和 delivery。未创建原生计划之前 schedule_enabled 只代表用户意图。

研究 JSON 与渲染器的最小结构如下。以下占位符是字段说明，不能作为实际报告的数据：

```json
{
  "title": "所选品类选品报告",
  "country": "<country>",
  "collected_at": "<actual timestamp>",
  "unique_product_target": 200,
  "sources": [{"name":"Best Sellers","url":"<observed URL>","target":100,"count":1,"note":"<coverage>"}],
  "products": [{
    "id":"amazon:<country>:<ASIN>","platform":"amazon","country":"<country>","product_id":"<ASIN>",
    "title":"<observed title>","url":"<product URL>","sources":["Best Sellers"],
    "source_ranks":[{"source":"Best Sellers","rank":1}],
    "brand":null,"rating":null,"rating_count":null,"review_count":null,
    "displayed_sales_message":null,"image_url":null,"image_scope":"product","gallery":[],
    "keywords":[],"pricing":{},"specifications":{},"feature_summary":null,"missing_reason":"<observed reason>"
  }],
  "reviews": [],"positive": [],"negative": [],"summary":"<evidence-based analysis>","opportunities": []
}
```

原始爬虫的 `product_id` 映射到报告 product_id；为每个商品构建 id；`product_url` 映射为 url。同一市场 ASIN 去重，sources 与 source_ranks 合并，不丢跨榜关联。source.count 等于实际关联该来源的去重商品数，不能填目标值。爬虫中嵌套 reviews 移到顶层，补 product_id（报告商品 id），同评论去重。保留原文、来源链接、日期、评分和 sampling。

关键词每条为 `{en,zh,category}`。category 使用 product_type/play/feature/material/use_case/audience/theme/ip；先语义提取和归一化，之后每 ASIN 每关键词计一次，覆盖率分母为全部有效商品。品牌不充当关键词抽取的替代品。

positive/negative 每项为 `{phrase,review_ids}`，必须引用真实评论。opportunities 每项为 `{title,reason,product_ids}`，必须引用主表商品。摘要清楚注明榜单与详情采集日期、评论样本局限。没有评论时保持空数组，不伪造例子。公开报告使用必要的短摘录或概述，不整段复制商品营销文案。

pricing 支持 current_price、reference_price、currency、currency_symbol、reference_label、source、discount_percent。数值未知为 null；只有当前价和较高参考价同时存在才计算差值百分比。标明实际币种；不能仅凭 `$` 推断美元。多币种不合并算价格统计。没有对应字段时保留 null，不补估算价。报告标题默认商品选品，不固定玩具。

gallery 每项 `{url,image_role,asin,scope,source}`，只有详情 ASIN 与榜单一致、主图资产匹配时记录 selected_asin，未证实则保留 product 图，不标为 SKU。specifications 保存实际规格原单位，feature_summary 为简短中文概述。

销量原文保存在 displayed_sales_message，识别到英文 past month/week/day 可简写数量加月/周/日；“月”指来源窗口，不是自然月。保留 K/M 及“+”含义，排序用下界，非月或未识别格式不参与月销量排序。rating_count 与文字评价数 review_count 不互相替代。
