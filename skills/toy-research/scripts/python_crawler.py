"""HTTP collection alternative. Outputs observed records; never invents ranks."""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from amazon_detail import parse_detail, AmazonVerificationRequired
from session_state import load_state


class PageAccessError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code=code


def web_url(value, base):
    if not value:
        return None
    result = urljoin(base, str(value))
    return result if urlparse(result).scheme in ("https", "http") else None


def parse_page(html, url, platform, country):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    if platform == "amazon":
        for card in soup.select('[id="gridItemRoot"], .zg-item-immersion'):
            links = card.select('a[href*="/dp/"]')
            if not links:
                continue
            link = next((a for a in links if len(a.get_text(strip=True)) > 15), links[0])
            match = re.search(r"/dp/([A-Z0-9]{10})", link.get("href", ""))
            if not match:
                continue
            image = card.select_one("img")
            rank_node = card.select_one(".zg-bdg-text")
            rank_match = re.search(r"\d+", rank_node.get_text()) if rank_node else None
            rating_node = card.select_one(".a-icon-alt")
            rating_raw = rating_node.get_text(strip=True) if rating_node else ""
            rating_match = re.search(r"\d+[.,]?\d*", rating_raw)
            products.append({
                "platform": platform, "country": country,
                "product_id": match[1],
                "title": link.get_text(strip=True) or (image.get("alt", "") if image else ""),
                "rank": int(rank_match[0]) if rank_match else None,
                "product_url": web_url(link.get("href"), url),
                "image_url": web_url(image.get("src"), url) if image else None,
                "image_scope": "product",
                "rating": float(rating_match[0].replace(",", ".")) if rating_match else None,
                "rating_raw": rating_raw,
            })
        known = {p['product_id'] for p in products}
        for node in soup.select('[data-client-recs-list]'):
            try:
                candidates = json.loads(node['data-client-recs-list'])
            except json.JSONDecodeError:
                continue
            for item in candidates:
                identifier = item.get('id','')
                rank = item.get('metadataMap',{}).get('render.zg.rank','')
                if identifier in known or not re.fullmatch(r'[A-Z0-9]{10}',identifier) or not str(rank).isdigit():
                    continue
                known.add(identifier)
                products.append({'platform':platform,'country':country,'product_id':identifier,
                                 'title':'','rank':int(rank),'product_url':web_url('/dp/'+identifier,url),
                                 'rank_source':'data-client-recs-list','needs_detail':True})
        products.sort(key=lambda p:p.get('rank') or 10**9)
        next_node = soup.select_one("li.a-last a")
    else:
        def visit(value):
            if isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, dict):
                types = value.get("@type", [])
                if isinstance(types, str):
                    types = [types]
                if "Product" in types:
                    product_url = web_url(value.get("url"), url)
                    identifier = value.get("productID") or value.get("sku") or product_url
                    image = value.get("image")
                    if isinstance(image, list):
                        image = image[0] if image else None
                    if isinstance(image, dict):
                        image = image.get("url")
                    brand = value.get("brand")
                    products.append({
                        "platform": platform, "country": country,
                        "product_id": str(identifier or ""), "title": value.get("name", ""),
                        "rank": None, "rank_scope": "未取得榜单排名",
                        "product_url": product_url, "image_url": web_url(image, url),
                        "image_scope": "product", "brand": brand.get("name") if isinstance(brand, dict) else brand,
                        "rating": (value.get("aggregateRating") or {}).get("ratingValue"),
                    })
                for item in value.values():
                    visit(item)
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                visit(json.loads(script.get_text()))
            except json.JSONDecodeError:
                continue
        next_node = soup.select_one('a[rel="next"]')
    delivery_node = soup.select_one("#glow-ingress-block")
    if not products:
        if platform=='amazon' and soup.select_one('form[action*="validateCaptcha"]'):
            raise PageAccessError('browser_challenge','Amazon 返回验证页面；请在浏览器完成验证并更新会话后再继续')
        if platform=='temu' and 'upload-static/assets/chl/js/' in html and 'challenge' in html:
            raise PageAccessError('browser_challenge','Temu 返回浏览器校验页面；使用用户会话验证后重试 Python，必要时使用 Playwright')
        if platform=='aliexpress' and 'login.aliexpress.com' in html and 'x5referer' in html:
            raise PageAccessError('login_required','AliExpress 返回登录跳转页面；请加载目标站点有效登录状态')
    return {
        "products": products,
        "next": web_url(next_node.get("href"), url) if next_node else None,
        "delivery": delivery_node.get_text(" ", strip=True) if delivery_node else "",
    }


def crawl(url, platform, country, limit=200, details=False, storage_state=None):
    source_url = url
    if platform not in ("amazon", "temu", "tiktok", "aliexpress"):
        raise ValueError("此 Python 爬虫尚未适配该平台")
    products, seen, visited = [], set(), set()
    delivery, pages, unresolved, declared_ranks = "", [], [], set()
    pagination_error = None
    collection_stop = None
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    auth = load_state(session, storage_state, url) if storage_state else None
    while url and url not in visited and len(products) < limit and len(visited) < 20:
        visited.add(url)
        try:
            response = session.get(url, timeout=40)
            response.raise_for_status()
        except requests.RequestException as error:
            if not products and not unresolved:
                raise
            pagination_error = str(error)
            break
        try:
            data = parse_page(response.text, response.url, platform, country)
        except PageAccessError as error:
            if not products and not unresolved: raise
            pagination_error=str(error)
            collection_stop={'phase':'pagination','url':response.url,'code':error.code,'reason':str(error)}
            break
        pages.append({"url": response.url, "declared": len(data["products"]),"rendered_titles":sum(bool(p['title']) for p in data['products'])})
        delivery = data["delivery"] or delivery
        for product in data["products"]:
            key = product["product_id"]
            if not key or key in seen:
                continue
            seen.add(key)
            if product.get('rank'):
                declared_ranks.add(product['rank'])
            if len(products) >= limit:
                continue
            if product.get('needs_detail'):
                if collection_stop:
                    unresolved.append({**product, 'deferred_reason':collection_stop['reason']})
                    continue
                try:
                    print('补齐内嵌榜单商品 '+key,file=sys.stderr)
                    detail_response = session.get(product['product_url'],timeout=40)
                    detail_response.raise_for_status()
                    product.update(parse_detail(detail_response.text,detail_response.url,key))
                except (ValueError, requests.RequestException) as error:
                    unresolved.append({**product, 'error':str(error)})
                    if isinstance(error, AmazonVerificationRequired):
                        collection_stop={'phase':'embedded_detail','product_id':key,
                                         'url':product['product_url'],'code':error.code,'reason':str(error)}
                    continue
            product.update({"collected_at": datetime.now(timezone.utc).isoformat(),
                            "sales_day": None, "sales_week": None, "sales_month": None,
                            "listed_at": product.get('listed_at')})
            products.append(product)
        url = data["next"]
        if collection_stop:
            break
    if not products and not unresolved:
        raise ValueError("HTTP 页面未取得商品；可能需要 JavaScript、登录或页面适配，可改用 Playwright")
    products = products[:limit]
    if details and platform == 'amazon' and not collection_stop:
        for product in products:
            if product.get('detail_source'):
                continue
            try:
                response = session.get(product['product_url'], timeout=40)
                response.raise_for_status()
                detail = parse_detail(response.text, response.url, product['product_id'])
                product.update({key:value for key,value in detail.items() if value is not None})
                product['detail_missing'] = [key for key in ['brand','listed_at','reviews'] if not detail.get(key)]
            except (ValueError, requests.RequestException) as error:
                product['detail_error'] = str(error)
                if isinstance(error, AmazonVerificationRequired):
                    collection_stop={'phase':'detail','product_id':product['product_id'],
                                     'url':product['product_url'],'code':error.code,'reason':str(error)}
                    break
    if collection_stop:
        for product in products:
            if not product.get('detail_source') and not product.get('detail_error'):
                product['detail_deferred_reason']=collection_stop['reason']
    observed_ranks = {p['rank'] for p in products if p.get('rank')}
    missing_ranks = sorted(rank for rank in declared_ranks if rank <= limit and rank not in observed_ranks)
    return {"source_url":source_url,"platform":platform,"country":country,
            "products": products[:limit], "observedDelivery": delivery, "pages": pages,
            'auth_state':auth,'unresolved_products':unresolved,'pagination_error':pagination_error,
            'collection_stop':collection_stop,'next_page':url,
            'coverage':{'target':limit,'actual':len(products),'missing':max(0,limit-len(products)),
                        'declared_rank_max':max(declared_ranks,default=None),'missing_declared_ranks':missing_ranks,
                        'source_range_shortfall':max(declared_ranks,default=0)<limit if not url and not collection_stop else None},
            "marketVerified": False,
            "note": "Python HTTP 采集，读取可用内嵌商品清单并补齐详情；无法补齐的商品单独列出。实际配送地区：" + (delivery or "未识别")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--country", required=True)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output")
    parser.add_argument("--details", action="store_true", help="补充 Amazon 详情页及可见评论")
    parser.add_argument("--storage-state", help="用户保存的 Playwright 登录状态 JSON")
    args = parser.parse_args()
    try:
        if not 1 <= args.limit <= 200:
            raise ValueError("limit 必须在 1–200 之间")
        result = crawl(args.url, args.platform, args.country, args.limit, args.details, args.storage_state)
        content = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as stream:
                stream.write(content)
        else:
            print(content)
    except (ValueError, OSError, requests.RequestException) as error:
        print(json.dumps({"error": str(error),"error_code":getattr(error,'code','collection_failed')}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
