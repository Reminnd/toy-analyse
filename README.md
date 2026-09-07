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

美国 Amazon 热销榜和新品榜各验证到第100名，合计200条榜单记录、193个去重商品；尚未实现每榜200条。样例报告分析36条定向评论样本，不代表全量消费者意见。

精确日周月销量、上架时间、完整SKU图片和部分品牌字段仍缺失。其他平台包含初始解析或API客户端，尚未完成真实接入验证。该仓库是二次开发交接版本，详细限制与下一步见 DEVELOPMENT.md。
