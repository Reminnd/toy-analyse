"""Render a Codex-authored, evidence-linked research JSON as HTML and JSON."""
import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlparse


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
        sales = esc(p.get('displayed_sales_message'))
        keywords = '<br>'.join(f'{esc(k.get("en"))} / {esc(k.get("zh"))}' if isinstance(k, dict) else f'{esc(k)} / 翻译缺失' for k in p.get('keywords', []))
        rankings = '<br>'.join(f'{esc(item.get("source"))} · 排名 {esc(item.get("rank"))}' for item in p.get('source_ranks', [{'source': p.get('source'), 'rank': p.get('rank')}]))
        cards.append(f'<tr><td>{picture}<small>{esc(p.get("image_scope"))}</small></td><td>{link(p.get("url"),p["title"])}<small>{esc(p["id"])}<br>{rankings}</small></td><td>{esc(p.get("brand"))}</td><td>{esc(p.get("rating"))}<small>评分数 {esc(p.get("rating_count"))}<br>文字评价数 {esc(p.get("review_count"))}</small></td><td>{sales}</td><td>{keywords}<small>{esc(p.get("missing_reason",""))}</small></td></tr>')
    recommendations = ''.join(f'<article><h3>{esc(o["title"])}</h3><p>{esc(o["reason"])}</p><small>商品依据：{esc(", ".join(o["product_ids"]))}</small></article>' for o in data.get("opportunities", []))
    review_rows = ''.join(f'<tr><td>{esc(r["id"])}<small>{esc(r["product_id"])}</small></td><td>{esc(r["text"])}<small>{"原文摘录" if r.get("is_excerpt") else "原文"} · {esc(r.get("sampling",""))}</small></td><td>{esc(r.get("rating"))}</td><td>{link(r.get("url"),r.get("date") or "原始评论")}</td></tr>' for r in reviews)

    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(data.get("title","玩具选品报告"))}</title>
<style>body{{font:15px/1.7 system-ui,"Microsoft YaHei";color:#203c32;background:#f2f4ee;margin:0}}main{{max-width:1400px;margin:auto;padding:32px}}header{{background:#1e4537;color:white;padding:30px;border-radius:14px}}section{{background:white;padding:25px;border-radius:12px;margin-top:22px}}h1{{margin:0}}h2{{font-size:20px}}p{{white-space:pre-wrap}}a{{color:#2d684d}}small,.muted{{display:block;color:#738075;font-size:12px}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #e3e9df;vertical-align:top}}img{{width:64px;height:70px;object-fit:contain}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.cloud{{min-height:160px;display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:16px;padding:20px;color:#2b754a}}.negative .cloud{{color:#ae5839}}.cloud span{{overflow-wrap:anywhere}}.scroll{{overflow:auto}}article{{border-left:3px solid #719568;padding:0 20px;margin:25px 0}}@media(max-width:750px){{main{{padding:12px}}.pair{{display:block}}}}</style></head><body><main>
<header><h1>{esc(data.get("title","玩具选品报告"))}</h1><div>{esc(data.get("country"))} · {esc(data.get("collected_at"))}</div></header>
<section><h2>数据覆盖</h2><ul>{sources}</ul><p>{esc(coverage)} 评论样本 {len(reviews)} 条。各榜单独立计数，跨榜重复 ASIN 仅计入主表一次；字段缺失不等于 0。合并商品集不代表单个官方 Top 200 榜单。</p></section>
<section><h2>AI 选品分析</h2><p>{esc(data.get("summary","未生成分析"))}</p>{recommendations}</section>
<section><h2>评论洞察与词云</h2><div class="pair"><div><h3>正面主题</h3>{cloud(data.get("positive",[]),len(reviews))}</div><div class="negative"><h3>负面主题</h3>{cloud(data.get("negative",[]),len(reviews))}</div></div></section>

<section><h2>商品明细</h2><div class="scroll"><table><tr><th>图片</th><th>商品</th><th>品牌</th><th>评分</th><th>销量原文</th><th>关键词（English / 中文）与缺失说明</th></tr>{''.join(cards)}</table></div></section>
<section><h2>评论证据</h2><div class="scroll"><table><tr><th>评论与商品 ID</th><th>原文</th><th>星级</th><th>来源</th></tr>{review_rows}</table></div></section></main></body></html>'''


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
