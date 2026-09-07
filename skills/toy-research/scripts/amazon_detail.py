"""Parse observed Amazon detail fields and visible review samples."""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def parse_detail(html, url, product_id):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("#productTitle")
    if not title:
        if soup.select_one('form[action*="validateCaptcha"]'):
            raise ValueError("Amazon 返回继续购物验证页面，未取得商品详情；需在浏览器完成验证后更新会话")
        raise ValueError("未取得商品详情标题，可能是登录或访问限制页面")
    asin = soup.select_one('input#ASIN')
    if asin and asin.get('value') and asin['value'] != product_id:
        raise ValueError("详情页商品 ID 与榜单商品不一致")
    attributes = {}
    for row in soup.select('#productOverview_feature_div tr, #productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr'):
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
        if not rid or rid in seen or body is None:
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
    sales = soup.select_one('#social-proofing-faceout-title-tk_bought')
    return {'title':title.get_text(' ',strip=True), 'brand':attributes.get('Brand') or attributes.get('品牌') or (brand_match[1] if brand_match else None),
            'rating':float(rating_match[0].replace(',','.')) if rating_match else None, 'rating_raw':rating_raw,
            'listed_at':attributes.get('Date First Available') or attributes.get('上架时间'),
            'listed_at_kind':'source_display', 'attributes':attributes,
            'rating_count':int(count_number) if count_number else None,'review_count':None,
            'image_url':(image.get('data-old-hires') or image.get('src')) if image else None,
            'image_scope':'product', 'displayed_sales_message':sales.get_text(' ',strip=True) if sales else None,
            'reviews':reviews, 'detail_source':url}
