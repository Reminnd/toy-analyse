# 采集与登录状态

## 命令

安装 Python 依赖：`python -m pip install -r <skill>/scripts/requirements.txt`。
需要浏览器时，在 scripts 目录执行 `npm ci`。浏览器脚本默认使用已安装的 Chrome；无 Chrome 时安装 Playwright Chromium 并使用 `--browser chromium`。脚本路径、输出路径含空格时按所在 shell 规则引号包裹。

先创建当前任务的 work 文件夹，按配置 sources 分别执行（country、URL、limit 均取配置值）：

```text
python scripts/python_crawler.py --platform amazon --country <country> --url <url> --limit 100 --details --output <work/source.json>
```

有保存的状态时附加 `--storage-state <work/.auth/amazon-state.json>`。优先加载来源自身配置的 storage_state，否则用顶层配置。核对真实页面配送国家/邮编，不能只看网站域名。脚本的 `marketVerified=false` 需要结合页面观察核对，不能直接改 true。

Python 使用 Requests 与 BeautifulSoup，不执行 JavaScript。读取榜单卡片、内嵌商品清单和真实下一页；缺标题的 ASIN 从详情补齐。`unresolved_products` 为尚未取得有效标题的记录，不能计入有效商品数量。`coverage.missing_declared_ranks` 帮助识别遗漏，`source_range_shortfall` 表示源范围不足的线索，仍须核对 pages 与 next_page。

Python 输出有缺口或动态内容时，用浏览器定向恢复：

```text
node scripts/playwright_crawler.mjs --platform amazon --country <country> --url <url> --limit 100 --details --python-result <work/source.json> --output <work/source-browser.json> --profile <work/browser>
```

可附加同一 `--storage-state`。首次 Python 完全未取得结果时省略 `--python-result`，正常读取两榜。检查浏览器结果的配送地区、恢复次数、原始排名和 ASIN 一致性后再合并。合并按市场+ASIN，并保留来源关联；新数据字段不应被另一来源空值覆盖。

`collection_stop` 出现时停止该来源 HTTP 请求；可以用同一用户会话做一次正常浏览器检查。浏览器也要求验证/登录时等待用户处理，不循环刷新，不规避验证。当前请求失败不删除已取得的数据。已采尽的公开范围不重复请求以期凑够 200。

## 登录快照

在用户可交互的终端执行：

```text
node scripts/save_session.mjs --url <marketplace-url> --output <work/.auth/amazon-state.json>
```

用户在浏览器完成登录及配送区域设置，回终端按 Enter。快照包含 cookies、localStorage/IndexedDB，可能包含会话凭证，只保存本机，不发聊天、不放公开仓库或客户包。Python 仅加载适用域名的有效 cookies 和 user-agent；快照可以帮助复用登录，但不等同完整浏览器状态，也不保证通过动态验证。失效时由用户重新保存，不能声称截图能恢复登录。

## 国家与分类缓存恢复

国家入口为 `https://www.amazon.com/customer-preferences/country?preferencesReturnUrl=%2F`；分类入口为所选站点的 `/Best-Sellers/zgbs`。`amazon_catalog.py` 按国家 select 与实际导航树解析，仅保存直接下级，不把上级导航混入子类。

若 HTTP 受限，但正常 Playwright 页面可访问，可将 `page.content()` 保存到 work，使用相同解析器和缓存接口：

```python
from pathlib import Path
from amazon_catalog import Catalog

observed_url = "<actual browser URL>"
html_file = Path("<saved browser HTML>")
catalog = Catalog("<workspace>/work/product-research-catalog.json",
                  fetch=lambda url: (html_file.read_text(encoding="utf-8"), observed_url))
# Only call the corresponding method for this observed page.
catalog.categories(observed_url, refresh=True)
# For the country-selector page, use catalog.markets(refresh=True).
```

先验证实际浏览器 URL 属于所选国家和请求类目。只在首次加载失败或用户明确更新时执行，不定时刷新选项。

不同国家页面可能不提供销量、参考价或相同的榜单。遇到未识别文案保留原文和空值，针对实际样本修正解析器后再填值，不根据国家猜字段。API 接口尚未内置；只有得到客户对应平台的准确文档、可用权限和环境变量名称后才扩展，缺少 API 不阻止原站路径。
