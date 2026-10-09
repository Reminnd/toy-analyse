# toy-analyse

用于 Codex 的玩具选品 skill/plugin：配置国家、平台和榜单链接，优先使用 Python，必要时使用 Playwright，输出包含评论词云的 HTML/JSON 选品报告，并通过 Codex 原生 automation 定时执行。

## 使用与开发

- [安装和使用](INSTALL.md)
- [二次开发交接与未完成项](DEVELOPMENT.md)
- [配置示例](config.example.json)
- [Skill 入口](skills/toy-research/SKILL.md)
- [美国 Amazon 样例报告](samples/amazon-us-toy-report-2026-09-07.html)

```sh
cd skills/toy-research/scripts
python -m pip install -r requirements.txt
npm install
python -m unittest discover -s tests -p "test_*.py"
node --test tests/sales.test.mjs
```

浏览器脚本默认使用本机 Chrome。登录状态在本机工作目录保存，不提交 Cookie 或 API 密钥。定时任务由 Codex 创建，克隆仓库不会自动启动定时任务。

## 当前状态

当前启用美国 Amazon，目标是热销榜与新品榜合计 **200 个不重复商品**，同一市场按 ASIN 去重；两榜公开范围各100名。历史样例包含200条榜单记录、193个不同商品，缺7个。可配置补充链接并保留独立来源和排名，不能将其冒充原榜排名。

报告显示来源返回的销量原文、中英文关键词、品牌、评分、当前 ASIN 主图及有评论依据的好差评词云。完整变体图片尚未实现；其他平台和卖家 API 未完成真实接入验证。样例分析36条定向评论，不代表全量消费者意见。

2026-10-09 更新了品牌扩展表解析、ASIN 图片关联与去重覆盖校验。最新探测发现本机会话配送地区已失效，运行美国日报前需重新验证地区。定时计划保持暂停；仓库不包含会话或 API 密钥。详细限制见 DEVELOPMENT.md。
