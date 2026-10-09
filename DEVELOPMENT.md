# 二次开发交接

本包为 Codex skill/plugin。当前仅启用美国 Amazon Toys & Games 的 Best Sellers 与 New Releases；Python 优先，Playwright 备用，分析和中英文关键词由 Codex 生成。入口是 `skills/toy-research/SKILL.md`。

## 当前范围

- 用户确认两榜合计目标200个不同商品，按同一市场ASIN去重。仅采现有两榜，接受跨榜重复造成的数量缺口，不添加子类目。
- 国家、榜单链接和运行时间通过 Codex 对话及配置文件修改。当前配置 US、Asia/Shanghai、19:00；配送参考 ZIP 10001。
- 使用 Codex 原生 automation，不部署独立网站、AI API或常驻调度器。原机器任务ID为 `amazon`，当前 PAUSED，不随ZIP迁移，安装不会启动定时任务。

## 最新实站结果（2026-10-09）

两榜各100条记录，去重后195个商品，差5个全部来自跨榜重复。HTTP补采期间出现验证页，同一美国会话在正常Chrome中可读取正确详情，浏览器补采已完成待处理请求。

| 数据项 | 已取得 |
| --- | ---: |
| 有标题及中英文关键词的商品 | 195 |
| 有详情的商品 | 193 |
| 品牌 | 187 |
| 评分 | 191 |
| 来源销量原文 | 174 |
| 图片 | 195 |
| 有页面ASIN关联的主图 | 192 |
| 去重可见评论 | 1976 |
| 本次语义分析评论样本 | 20 |

报告包含正负词云与5个有商品、评论依据的选品方向。评论为10个商品的定向样本，可能跨变体、国家和时间，不代表总体评价率。样例文件在 `samples/amazon-us-toy-report-2026-10-09.html` 和对应JSON。

## 尚未完成的部分

- B0FJ31ZCRB 和 B0HJRRVCWV 的详情页ASIN与原榜单不一致，未合并错变体详情。前者已通过原始榜单卡片恢复标题、评分、商品图。
- 部分页面不返回品牌、评分或销量文案，保留缺失。销量直接使用来源原文，不估算精确日周月销量。
- 图片仅为列表商品图或当前ASIN主图，没有卖家内部SKU及全部变体图集。不同范围在报告中标注。
- 其他平台及 SellerSprite、FastMoss API脚本为历史初始实现，未启用或完成真实账户验证。用户尚未配置API；选品助手链接暂定。
- 尚无其他国家及特定Codex模型的独立端到端验证，不应从美国验证结果推断全部市场均已适配。

## 采集和恢复

Python从实际商品卡片及 `data-client-recs-list` 读取ASIN与原排名，跟随真实分页。完整标题未取得的记录保存在 `unresolved_products`。验证页出现后停止该HTTP来源请求，保存 `collection_stop`、未读分页及未请求详情，区分失败和延后。

`playwright_crawler.mjs --python-result <raw.json> --details` 消费Python结果，只处理缺口与未完成详情。使用正常浏览器先确认目标地区和页面可用性；浏览器也要求验证时停止并由用户处理。标题缺失且Python已确认详情ASIN不一致时，改读原榜单卡片，必须同时匹配ASIN和排名，不重新请求已知错变体详情。

会话通过 `save_session.mjs` 保存，Python通过 `session_state.py` 复用有效Cookie；这不等于执行浏览器JavaScript或永久登录。每轮核对实际配送地区。详细参数和边界见 `references/python-collection.md`。

## 安装和测试

在 `skills/toy-research/scripts/` 运行：

```sh
python -m pip install -r requirements.txt
npm install
python -m unittest discover -s tests -p "test_*.py"
node --test tests/sales.test.mjs tests/recovery.test.mjs
node --test tests/list_card.test.mjs
```

最后一项需要本机Chrome，使用本地拦截页面，不访问Amazon。已验证18项Python测试、5项恢复测试、1项浏览器卡片测试及2项销量窗口测试；实站证据另见上述最新结果。测试通过不表示所有在线字段都可获取。

`config.example.json` 复制为任务目录的 `toy-research.config.json` 后修改。Cookie和浏览器状态保存在 `work/.auth/`，不提交仓库或打包；包内不含API密钥、node_modules和完整原始评论。报告样例仅保留短摘录和原始评论链接。安装说明见 `INSTALL.md`。
