"""Evidence-based charts for product prices, brands and bilingual title terms."""
import html
from collections import Counter
from statistics import median


def esc(value):
    return html.escape(str(value), quote=True)


def dashboard(products):
    priced = [p for p in products if p.get('pricing', {}).get('currency') == 'USD'
              and isinstance(p['pricing'].get('current_price'), (int, float))]
    prices = [p['pricing']['current_price'] for p in priced]
    brands = Counter(p['brand'] for p in products if p.get('brand'))
    terms = Counter()
    for p in products:
        terms.update({(k['en'], k['zh']) for k in p.get('keywords', []) if isinstance(k, dict)})
    galleries = sum(bool(p.get('gallery')) for p in products)
    midpoint = f'${median(prices):,.2f}' if prices else '暂无数据'
    cards = ''.join(f'<div class="metric"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>' for label, value, note in [
        ('去重商品',len(products),'每个 ASIN 计一次'),('售价中位数',midpoint,f'USD 有效样本 {len(prices)} 个'),
        ('已识别品牌',len(brands),f'品牌缺失 {len(products)-sum(brands.values())} 个'),('已取得图集',galleries,'当前 ASIN 页面图集')])
    def bars(entries):
        peak = max((n for _, n in entries), default=1) or 1
        return ''.join(f'<div class="chart-row"><span>{esc(label)}</span><div class="bar-track"><div class="bar-fill" style="width:{n/peak*100:.2f}%"></div></div><b>{n}</b></div>' for label,n in entries)
    bins = [('低于 $10',sum(v<10 for v in prices)),('$10–20',sum(10<=v<20 for v in prices)),
            ('$20–50',sum(20<=v<50 for v in prices)),('$50–100',sum(50<=v<100 for v in prices)),
            ('$100 及以上',sum(v>=100 for v in prices))]
    brand_bars = bars(brands.most_common(8)) if brands else '<p>品牌数据未取得</p>'
    price_bars = bars(bins) if prices else '<p>尚未取得可比较的 USD 商品售价。</p>'
    categories = {'product_type':'品类','play':'玩法','feature':'特征','material':'材质','use_case':'场景/用途','audience':'人群','theme':'主题','ip':'IP','other':'其他'}
    category_by_term = {(k['en'],k['zh']):k.get('category','other') for p in products for k in p.get('keywords',[]) if isinstance(k,dict)}
    peak = max(terms.values(), default=1)
    cloud = ''.join(f'<button class="term" data-search="{esc(zh)}" data-keyword="{esc(en)}" data-category="{esc(category_by_term[(en,zh)])}" style="font-size:{14+round(18*n/peak)}px" title="{n} 个商品"><span>{esc(en)}</span><small>{esc(zh)} · {n}</small></button>' for (en,zh),n in terms.most_common())
    keyword_rows = ''.join(f'<tr data-category="{esc(category_by_term[(en,zh)])}"><td>{esc(categories.get(category_by_term[(en,zh)],"其他"))}</td><td><button data-search="{esc(zh)}" data-keyword="{esc(en)}">{esc(en)} / {esc(zh)}</button></td><td>{n}</td><td>{n/len(products):.1%}</td></tr>' for (en,zh),n in terms.most_common())
    category_options = ''.join(f'<option value="{key}">{label}</option>' for key,label in categories.items() if key in category_by_term.values())
    discounted = [p for p in priced if p['pricing'].get('discount_percent') is not None]
    pairs = sorted(discounted,key=lambda p:p['pricing']['discount_percent'],reverse=True)
    comparisons = ''
    for p in pairs:
        pr=p['pricing'];current=pr['current_price'];reference=pr['reference_price']
        comparisons += f'<div class="price-comparison"><p title="{esc(p["title"])}">{esc(p["title"][:65])}</p><div class="compare-reference" style="width:100%"></div><div class="compare-current" style="width:{current/reference*100:.2f}%"></div><small>当前 ${current:.2f} · 参考 ${reference:.2f} · 差额 {pr["discount_percent"]:.2f}%</small></div>'
    if not comparisons: comparisons='<p>没有同时取得当前售价和更高参考价的商品，不推算折扣。</p>'
    return f'''<section class="dashboard"><h2>选品数据看板</h2><div class="metrics">{cards}</div>
<div class="chart-grid"><article><h3>商品单价分布 · USD</h3>{price_bars}<small>价格区间左闭右开；这是商品售价分布，不是订单客单价。</small></article>
<article><h3>品牌分布 · 前 8 名</h3>{brand_bars}<small>按本次去重商品数统计，不代表市场份额或品牌销量。</small></article>
<article><h3>当前售价 vs 来源参考价</h3><p><small>灰色：每组参考价 = 100% · 橙色：当前价占比；按价差比例排序，可滚动查看全部。</small></p><div class="price-comparisons">{comparisons}</div><small>展示全部 {len(discounted)} 个可计算价差样本；参考价含义以商品明细原标签为准。优惠券、会员或信用卡优惠未自动叠加。</small></article>
<article><h3>标题关键词 · English / 中文</h3><p>{len(products)} 个标题 · {len(terms)} 个归一化关键词 · {sum(terms.values())} 次商品关联</p><label>关键词维度 <select id="keyword-category"><option value="all">全部</option>{category_options}</select></label><div class="title-cloud">{cloud}</div><small>一标题多词，同义词归一；每个ASIN对每词计一次。标题宣称不等于实测效果，词频不是搜索量。点击词语精确筛选商品。</small><details class="keyword-statistics"><summary>查看全部关键词频次与商品覆盖率</summary><div class="keyword-table"><table><thead><tr><th>维度</th><th>English / 中文</th><th>商品数</th><th>覆盖率</th></tr></thead><tbody>{keyword_rows}</tbody></table></div></details></article></div></section>'''


STYLE = '''[hidden]{display:none!important}.title-cloud{max-height:440px;overflow:auto;align-content:flex-start}.price-comparisons{max-height:560px;overflow:auto;padding-right:12px}.keyword-table{max-height:480px;overflow:auto}.keyword-statistics{margin-top:18px}#keyword-category{padding:7px;font:inherit;border:1px solid #b9cbbb;border-radius:6px}.keyword-table button{border:0;background:none;color:#315d40;text-align:left;cursor:pointer;font:inherit}.keyword-table td{font-size:12px}.keyword-table table{min-width:0;width:100%}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:20px 0}.metric{background:#eef4ef;border:1px solid #dce7dc;padding:20px;border-radius:12px}.metric span{font-size:13px;color:#526d5a}.metric strong{display:block;font-size:30px;line-height:1.7}.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:26px}.chart-grid article{border:1px solid #e3e9df;border-radius:12px;padding:22px;margin:0;min-width:0}.chart-row{display:grid;grid-template-columns:145px 1fr 32px;gap:10px;align-items:center;margin:14px 0;font-size:12px}.chart-row span{overflow-wrap:anywhere}.bar-track{background:#edf1eb;border-radius:4px;overflow:hidden;height:12px}.bar-fill{background:#548167;height:100%;min-width:0}.title-cloud{display:flex;flex-wrap:wrap;justify-content:center;gap:12px;padding:14px 0}.term{font-family:inherit;border:0;border-radius:8px;background:#f0f5ec;color:#315d40;padding:9px;cursor:pointer}.term:hover{background:#dcebd5}.term small{font-size:12px}.price-comparison{margin:15px 0}.price-comparison p{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:0 0 5px}.compare-reference{height:6px;background:#c7cec4;border-radius:3px}.compare-current{height:9px;background:#c88b51;border-radius:3px;margin:3px 0}.product-gallery{display:flex;flex-wrap:wrap;gap:7px;margin:10px 0}.product-gallery img{border:1px solid #e1e7dd;border-radius:6px;background:white;width:78px;height:78px}.search-box{width:min(100%,520px);padding:12px;border:1px solid #b9cbbb;border-radius:8px;font:inherit;margin:0 0 18px}.price-value{font-weight:700;white-space:nowrap}.reference-price{color:#7b847c;font-size:12px}dialog{border:0;border-radius:14px;padding:20px;max-width:90vw;background:#fff}dialog::backdrop{background:#14271ed9}dialog img{display:block;width:auto;height:auto;max-width:80vw;max-height:75vh;object-fit:contain}dialog button{padding:9px 16px;margin:8px;font:inherit;cursor:pointer}@media(max-width:850px){.metrics{grid-template-columns:repeat(2,1fr)}.chart-grid{grid-template-columns:1fr}.chart-row{grid-template-columns:110px 1fr 25px}}'''

INTERACTION = '''<dialog id="gallery-dialog"><button id="gallery-close">关闭</button><button id="gallery-prev">上一张</button><button id="gallery-next">下一张</button><span id="gallery-count"></span><img id="gallery-image" alt="当前商品图集"></dialog><script>
const search=document.getElementById('product-search');let selectedKeyword=null;
function filterProducts(){const term=search.value.trim().toLowerCase();document.querySelectorAll('#product-table tbody tr[data-product]').forEach(row=>row.hidden=selectedKeyword?!JSON.parse(row.dataset.keywords||'[]').includes(selectedKeyword):!row.innerText.toLowerCase().includes(term));}
search.addEventListener('input',()=>{selectedKeyword=null;filterProducts();});
document.querySelectorAll('[data-search]').forEach(button=>button.addEventListener('click',()=>{selectedKeyword=button.dataset.keyword;search.value=button.dataset.search;filterProducts();search.scrollIntoView({behavior:'smooth',block:'center'});}));
document.getElementById('keyword-category').addEventListener('change',event=>{document.querySelectorAll('[data-category]').forEach(node=>node.hidden=event.target.value!=='all'&&node.dataset.category!==event.target.value);});
const modal=document.getElementById('gallery-dialog');let galleryURLs=[],galleryIndex=0;
function showImage(){document.getElementById('gallery-image').src=galleryURLs[galleryIndex];document.getElementById('gallery-count').textContent=(galleryIndex+1)+' / '+galleryURLs.length;}
document.querySelectorAll('.product-gallery a').forEach(anchor=>anchor.addEventListener('click',event=>{event.preventDefault();galleryURLs=[...anchor.closest('.product-gallery').querySelectorAll('a')].map(a=>a.href);galleryIndex=galleryURLs.indexOf(anchor.href);showImage();modal.showModal();}));
document.getElementById('gallery-close').onclick=()=>modal.close();document.getElementById('gallery-prev').onclick=()=>{galleryIndex=(galleryIndex-1+galleryURLs.length)%galleryURLs.length;showImage();};document.getElementById('gallery-next').onclick=()=>{galleryIndex=(galleryIndex+1)%galleryURLs.length;showImage();};
</script>'''
