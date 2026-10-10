"""Render a Codex-authored, evidence-linked research JSON as HTML and JSON."""
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from report_visuals import dashboard, STYLE, INTERACTION


def sales_display(message):
    if not message:
        return '—（缺失）'
    match = re.fullmatch(r'([\d,.]+\s*[KMB]?\+?)\s+bought in (?:the )?past (month|week|day)', message.strip(), re.I)
    if match:
        period = {'month':'月','week':'周','day':'日'}[match[2].lower()]
        return f'{match[1]}（{period}）'
    return f'{message}（周期未识别）'


def esc(value):
    return html.escape(str(value if value is not None else "缺失"), quote=True)


def link(url, label):
    if url and urlparse(url).scheme in ("https", "http"):
        return f'<a href="{esc(url)}">{esc(label)}</a>'
    return esc(label)


def validate(data):
    products = data.get("products", [])
    ids = [p["id"] for p in products]
    if len(set(ids)) != len(ids):
        raise ValueError("商品主表存在重复 id")
    asin_keys = [(p.get('country', data.get('country')), p['product_id'])
                 for p in products if p.get('platform') == 'amazon' and p.get('product_id')]
    if len(set(asin_keys)) != len(asin_keys):
        raise ValueError("同一市场的 Amazon ASIN 重复")
    for product in products:
        for keyword in product.get('keywords', []):
            if isinstance(keyword, dict) and not all(isinstance(keyword.get(lang), str) and keyword[lang].strip() for lang in ('en', 'zh')):
                raise ValueError("关键词必须同时包含非空英文 en 和中文 zh")
    for source in data.get("sources", []):
        observed = sum(1 for p in products if source["name"] in p.get("sources", [p.get("source")]))
        if source["count"] != observed:
            raise ValueError("来源条数与实际商品关联不一致")
    reviews = data.get("reviews", [])
    review_ids = [r["id"] for r in reviews]
    if len(set(review_ids)) != len(review_ids):
        raise ValueError("评论 id 重复")
    for r in reviews:
        if r["product_id"] not in ids or not r.get("text", "").strip():
            raise ValueError("评论缺少有效商品关联或原文")
    for group in ("positive", "negative"):
        for theme in data.get(group, []):
            refs = theme.get("review_ids", [])
            if not refs or not set(refs).issubset(review_ids):
                raise ValueError("词云主题必须引用实际存在的评论")
    for item in data.get("opportunities", []):
        if not item.get("product_ids") or not set(item["product_ids"]).issubset(ids):
            raise ValueError("选品建议必须引用实际存在的商品")


def cloud(themes, total):
    if not themes:
        return '<p class="muted">未取得可分析的主题；不生成词云。</p>'
    counts = [(t["phrase"], len(set(t["review_ids"]))) for t in themes]
    counts.sort(key=lambda item: item[1], reverse=True)
    largest = counts[0][1]
    words = ''.join(f'<span style="font-size:{16+round(26*n/largest)}px" title="{n} 条评论">{esc(phrase)}</span>' for phrase, n in counts)
    table = ''.join(f'<tr><td>{esc(phrase)}</td><td>{n} / {total}</td></tr>' for phrase, n in counts)
    return f'<div class="cloud">{words}</div><table><tr><th>主题</th><th>评论数 / 样本总数</th></tr>{table}</table>'


def detail_information(product):
    specs = ''.join(f'<dt>{esc(key)}</dt><dd>{esc(value)}</dd>'
                    for key, value in product.get('specifications', {}).items())
    summary = product.get('feature_summary')
    gallery = product.get('gallery', [])
    if not specs and not summary and not gallery:
        return ''
    description = f'<p>{esc(summary)}</p>' if summary else ''
    pictures = ''.join(f'<a href="{esc(item["url"])}"><img src="{esc(item["url"])}" alt="{esc(item.get("image_role") or "商品图集")}" loading="lazy"></a>'
                       for item in gallery if urlparse(item.get('url','')).scheme in ('http','https'))
    images = f'<p>当前 ASIN 图集（{len(gallery)} 张，点击查看原图）</p><div class="product-gallery">{pictures}</div>' if gallery else ''
    return f'<details><summary>展开详情规格与商品要点</summary>{description}<dl>{specs}</dl>{images}<small>来源页面提供；商品宣传不等于独立测试结论。</small></details>'


def render(data):
    validate(data)
    products = data.get("products", [])
    reviews = data.get("reviews", [])
    sources = ''.join(f'<li>{link(s.get("url"),s["name"])}：{esc(s["count"])}/{esc(s.get("target",200))} · {esc(s.get("note",""))}</li>' for s in data.get("sources", []))
    target = data.get('unique_product_target', 200)
    coverage = f'合计目标 {target} 个不重复商品；实际 {len(products)} 个；缺口 {max(0, target - len(products))} 个。'
    cards = []
    for p in products:
        image = p.get("image_url")
        picture = f'<img src="{esc(image)}" alt="商品图" loading="lazy">' if image and urlparse(image).scheme in ("http", "https") else '<span>图片缺失</span>'
        if p.get('image_asin'):
            picture += f'<small>ASIN {esc(p["image_asin"])}</small>'
        sales = f'<span class="sales-value" title="{esc(p.get("displayed_sales_message") or "来源未提供销量")}">{esc(sales_display(p.get("displayed_sales_message")))}</span>'
        pricing = p.get('pricing') or {}
        current = pricing.get('current_price')
        price_cell = f'<span class="price-value">{esc(pricing.get("currency") or pricing.get("currency_symbol") or "币种未知")} {current:.2f}</span>' if current is not None else '未取得'
        if pricing.get('reference_price') is not None:
            price_cell += f'<small class="reference-price">参考价 <del>{pricing["reference_price"]:.2f}</del></small><small>{esc(pricing.get("reference_label") or "来源参考价")}</small>'
        if pricing.get('discount_percent') is not None:
            price_cell += f'<small>价差 {pricing["discount_percent"]:.2f}%</small>'
        keywords = '<br>'.join(f'{esc(k.get("en"))} / {esc(k.get("zh"))}' if isinstance(k, dict) else f'{esc(k)} / 翻译缺失' for k in p.get('keywords', []))
        rankings = '<br>'.join(f'{esc(item.get("source"))} · 排名 {esc(item.get("rank"))}' for item in p.get('source_ranks', [{'source': p.get('source'), 'rank': p.get('rank')}]))
        keyword_data = esc(json.dumps([k['en'] for k in p.get('keywords',[]) if isinstance(k,dict)]))
        cards.append(f'<tr data-product data-keywords="{keyword_data}"><td>{picture}<small>{esc(p.get("image_scope"))}</small></td><td>{link(p.get("url"),p["title"])}<small>{esc(p["id"])}<br>{rankings}</small>{detail_information(p)}</td><td>{esc(p.get("brand"))}</td><td>{esc(p.get("rating"))}<small>评分数 {esc(p.get("rating_count"))}<br>文字评价数 {esc(p.get("review_count"))}</small></td><td>{price_cell}</td><td>{sales}</td><td>{keywords}<small>{esc(p.get("missing_reason",""))}</small></td></tr>')
    recommendations = ''.join(f'<article><h3>{esc(o["title"])}</h3><p>{esc(o["reason"])}</p><small>商品依据：{esc(", ".join(o["product_ids"]))}</small></article>' for o in data.get("opportunities", []))
    review_rows = ''.join(f'<tr><td>{esc(r["id"])}<small>{esc(r["product_id"])}</small></td><td>{esc(r["text"])}<small>{"原文摘录" if r.get("is_excerpt") else "原文"} · {esc(r.get("sampling",""))}</small></td><td>{esc(r.get("rating"))}</td><td>{link(r.get("url"),r.get("date") or "原始评论")}</td></tr>' for r in reviews)

    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(data.get("title","玩具选品报告"))}</title>
<style>body{{font:15px/1.7 system-ui,"Microsoft YaHei";color:#30251f;background:#fff8f2;margin:0}}main{{max-width:1400px;margin:auto;padding:32px}}header{{background:linear-gradient(115deg,#f25b05,#ff8a24);box-shadow:0 8px 24px #ef70151a;color:white;padding:30px;border-radius:14px}}section{{background:white;border:1px solid #f4e6d9;box-shadow:0 4px 18px #aa5a1206;padding:25px;border-radius:12px;margin-top:22px}}h1{{margin:0}}h2{{font-size:20px}}p{{white-space:pre-wrap}}a{{color:#b94700}}small,.muted{{display:block;color:#80736b;font-size:12px}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #f2e5da;vertical-align:top}}img{{width:64px;height:70px;object-fit:contain}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.cloud{{min-height:160px;display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:16px;padding:20px;color:#b94d06}}.negative .cloud{{color:#7e4939}}.cloud span{{overflow-wrap:anywhere}}.scroll{{overflow:auto}}article{{border-left:3px solid #ff922e;padding:0 20px;margin:25px 0}}@media(max-width:750px){{main{{padding:12px}}.pair{{display:block}}}}{STYLE}</style></head><body><main>
<header><h1>{esc(data.get("title","玩具选品报告"))}</h1><div>{esc(data.get("country"))} · {esc(data.get("collected_at"))}</div></header>
<section><h2>数据覆盖</h2><ul>{sources}</ul><p>{esc(coverage)} 评论样本 {len(reviews)} 条。各榜单独立计数，跨榜重复 ASIN 仅计入主表一次；字段缺失不等于 0。合并商品集不代表单个官方 Top 200 榜单。</p></section>
{dashboard(products)}
<section><h2>AI 选品分析</h2><p>{esc(data.get("summary","未生成分析"))}</p>{recommendations}</section>
<section><h2>评论洞察与词云</h2><div class="pair"><div><h3>正面主题</h3>{cloud(data.get("positive",[]),len(reviews))}</div><div class="negative"><h3>负面主题</h3>{cloud(data.get("negative",[]),len(reviews))}</div></div></section>

<section><h2>商品明细</h2><input id="product-search" class="search-box" placeholder="筛选标题、品牌或中英文关键词" aria-label="筛选商品"><div class="scroll"><table id="product-table"><tr><th>图片</th><th>商品</th><th>品牌</th><th>评分</th><th>当前售价 / 参考价</th><th>销量</th><th>关键词（English / 中文）与缺失说明</th></tr>{''.join(cards)}</table></div></section>
<section><h2>评论证据</h2><div class="scroll"><table><tr><th>评论与商品 ID</th><th>原文</th><th>星级</th><th>来源</th></tr>{review_rows}</table></div></section></main>{INTERACTION}</body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    content = render(data)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    output.with_suffix(".json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
