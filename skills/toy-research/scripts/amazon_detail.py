"""Parse observed Amazon detail fields and visible review samples."""
import re
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


class AmazonVerificationRequired(ValueError):
    code = 'browser_challenge'


def parse_detail(html, url, product_id):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("#productTitle")
    if not title:
        if soup.select_one('form[action*="validateCaptcha"]'):
            raise AmazonVerificationRequired("Amazon 返回继续购物验证页面，未取得商品详情；需在浏览器完成验证后更新会话")
        raise ValueError("未取得商品详情标题，可能是登录或访问限制页面")
    asin = soup.select_one('input#ASIN')
    if asin and asin.get('value') and asin['value'] != product_id:
        raise ValueError("详情页商品 ID 与榜单商品不一致")
    attributes = {}
    for row in soup.select('#productOverview_feature_div tr, #productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr, #productDetails_expanderTables_depthLeftSections tr'):
        cells = row.find_all(['th', 'td'], recursive=False)
        if len(cells) == 2:
            attributes[cells[0].get_text(' ', strip=True).strip(': \u200e\u200f')] = cells[1].get_text(' ', strip=True)
    for row in soup.select('#detailBullets_feature_div li'):
        label = row.select_one('.a-text-bold')
        if label:
            key = label.get_text(' ', strip=True).strip(': \u200e\u200f')
            attributes[key] = row.get_text(' ', strip=True).replace(label.get_text(' ', strip=True), '', 1).strip(' :\u200e\u200f')
    reviews = []
    seen = set()
    for row in soup.select('[data-hook="review"]'):
        rid = row.get('id')
        body = row.select_one('[data-hook="reviewRichContentContainer"], [data-hook="review-body"]')
        if not rid or rid in seen or body is None or not body.get_text(' ', strip=True):
            continue
        seen.add(rid)
        rating = row.select_one('[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]')
        number = re.search(r'\d+[.,]?\d*', rating.get_text()) if rating else None
        date = row.select_one('[data-hook="review-date"]')
        variation = row.select_one('[data-hook="format-strip"]')
        reviews.append({'id':rid,'text':body.get_text(' ',strip=True),
                        'rating':float(number[0].replace(',','.')) if number else None,
                        'date':date.get_text(' ',strip=True) if date else None,
                        'variation':variation.get_text(' ',strip=True) if variation else None,
                        'url':urljoin(url,'/gp/customer-reviews/'+rid),
                        'sampling':'商品详情页可见评论；可能包含多个变体'})
    count = soup.select_one('#acrCustomerReviewText')
    count_number = re.sub(r'[^\d]', '', count.get_text()) if count else ''
    byline = soup.select_one('#bylineInfo')
    brand_match = re.match(r'Brand:\s*(.+)', byline.get_text(' ', strip=True)) if byline else None
    rating_node = soup.select_one('#acrPopover')
    rating_raw = (rating_node.get('title') or rating_node.get_text(' ', strip=True)) if rating_node else ''
    rating_match = re.search(r'\d+[.,]?\d*', rating_raw)
    image = soup.select_one('#landingImage, #imgBlkFront')
    image_asin = asin.get('value') if asin and asin.get('value') == product_id and image else None
    gallery = []
    if image_asin:
        for script in soup.find_all('script'):
            match = re.search(r"'colorImages'\s*:\s*\{\s*'initial'\s*:\s*A\.\$\.parseJSON\('((?:\\.|[^'\\])*)'\)", script.get_text())
            if not match:
                continue
            try:
                images = json.loads(match[1].replace("\\'", "'"))
            except json.JSONDecodeError:
                continue
            main = next((item for item in images if item.get('variant') == 'MAIN'), {})
            displayed_asset = re.search(r'/images/I/([^/.]+)', image.get('data-old-hires') or image.get('src') or '')
            gallery_asset = re.search(r'/images/I/([^/.]+)', main.get('hiRes') or main.get('large') or '')
            if not displayed_asset or not gallery_asset or displayed_asset[1] != gallery_asset[1]:
                continue
            seen_urls = set()
            for item in images:
                source = item.get('hiRes') or item.get('large')
                if source and source.startswith(('https://', 'http://')) and source not in seen_urls:
                    seen_urls.add(source)
                    gallery.append({'url':source,'image_role':item.get('variant'),
                                    'asin':image_asin,'scope':'selected_asin','source':url})
            if gallery:
                break
    sales = soup.select_one('#social-proofing-faceout-title-tk_bought')
    price_root = soup.select_one('#corePriceDisplay_desktop_feature_div') or soup.select_one('#corePrice_feature_div')
    def amount(node):
        if node is None:
            return None
        whole, fraction = node.select_one('.a-price-whole'), node.select_one('.a-price-fraction')
        if whole:
            digits = re.sub(r'\D', '', whole.get_text())
            if digits:
                return float(digits + '.' + (re.sub(r'\D', '', fraction.get_text()) if fraction else '0'))
        raw = node.select_one('.a-offscreen')
        match = re.search(r'([\d,]+\.\d{2})', raw.get_text() if raw else '')
        return float(match[1].replace(',', '')) if match else None
    current_node = price_root.select_one('.priceToPay, .apex-pricetopay-value') if price_root else None
    reference_node = price_root.select_one('.basisPrice .a-text-price') if price_root else None
    current_price, reference_price = amount(current_node), amount(reference_node)
    symbol_node = current_node.select_one('.a-price-symbol') if current_node else None
    symbol = symbol_node.get_text(strip=True) if symbol_node else None
    currency = {'€':'EUR','£':'GBP'}.get(symbol)
    if symbol == '$' and urlparse(url).hostname in ('amazon.com','www.amazon.com'):
        currency = 'USD'
    basis = price_root.select_one('.basisPrice') if price_root else None
    pricing = {'current_price':current_price,'reference_price':reference_price,'currency':currency,
               'currency_symbol':symbol,'reference_label':basis.get_text(' ',strip=True) if basis else None,
               'source':url,'discount_percent':round((1-current_price/reference_price)*100,2)
               if current_price is not None and reference_price and reference_price>current_price else None}
    feature_bullets = list(dict.fromkeys(
        node.get_text(' ', strip=True) for node in soup.select('#feature-bullets li .a-list-item')
        if node.get_text(' ', strip=True)))
    return {'title':title.get_text(' ',strip=True), 'brand':attributes.get('Brand') or attributes.get('Brand Name') or attributes.get('品牌') or (brand_match[1] if brand_match else None),
            'rating':float(rating_match[0].replace(',','.')) if rating_match else None, 'rating_raw':rating_raw,
            'listed_at':attributes.get('Date First Available') or attributes.get('上架时间'),
            'listed_at_kind':'source_display', 'attributes':attributes,
            'rating_count':int(count_number) if count_number else None,'review_count':None,
            'image_url':(image.get('data-old-hires') or image.get('src')) if image else None,
            'image_scope':'selected_asin' if image_asin else 'product', 'image_asin':image_asin, 'displayed_sales_message':sales.get_text(' ',strip=True) if sales else None,
            'pricing':pricing,'gallery':gallery,'gallery_status':'embedded_initial' if gallery else 'not_observed',
            'feature_bullets':feature_bullets, 'reviews':reviews, 'detail_source':url}
