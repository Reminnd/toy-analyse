"""Discover Amazon marketplace and category choices; cache only observed pages."""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

MARKETS_URL = 'https://www.amazon.com/customer-preferences/country?preferencesReturnUrl=%2F'
COUNTRY_CODES = {'com': 'US', 'com.au': 'AU', 'com.be': 'BE', 'com.br': 'BR',
                 'ca': 'CA', 'cn': 'CN', 'eg': 'EG', 'fr': 'FR', 'de': 'DE',
                 'in': 'IN', 'ie': 'IE', 'it': 'IT', 'co.jp': 'JP', 'com.mx': 'MX',
                 'nl': 'NL', 'pl': 'PL', 'sa': 'SA', 'sg': 'SG', 'co.za': 'ZA',
                 'es': 'ES', 'se': 'SE', 'com.tr': 'TR', 'ae': 'AE', 'co.uk': 'GB'}


def parse_markets(html, url=MARKETS_URL):
    soup = BeautifulSoup(html, 'html.parser')
    result, seen = [], set()
    for option in soup.select('select#icp-dropdown option'):
        target = urlsplit(urljoin(url, option.get('value') or '/'))
        host = target.hostname or ''
        if not host.startswith('www.amazon.') or host in seen:
            continue
        seen.add(host)
        suffix = host.removeprefix('www.amazon.')
        result.append({'label': option.get_text(' ', strip=True),
                       'country': COUNTRY_CODES.get(suffix, suffix.upper()),
                       'origin': 'https://' + host})
    if not result:
        raise ValueError('未识别 Amazon 国家选择器；请在浏览器检查页面或登录后重试。')
    return result


def category_key(url):
    path = urlsplit(url).path
    for marker in ('/zgbs/', '/gp/new-releases/'):
        if marker in path:
            return path.split(marker, 1)[1].split('/ref=')[0].strip('/')
    return ''


def parse_categories(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    root = soup.select_one('ul[class*="zg-browse-root"], #zg_browseRoot, [role="tree"]')
    if root is None:
        raise ValueError('未识别分类树；可能需要登录、浏览器验证，或该站点未提供此榜单。')
    selected = root.select_one('[aria-current="page"], .zg_selected, [class*="zg-selected"]')
    if selected:
        current = selected.find_parent('li')
        sibling = current.find_next_sibling('li') if current else None
        group = sibling.find('ul') if sibling else None
    else:
        group = root.select_one('ul[class*="zg-browse-group"]') or root
    result, seen = [], set()
    for row in group.find_all('li', recursive=False) if group else []:
        anchor = row.find('a', href=True)
        if anchor is None:
            continue
        target = urljoin(url, anchor['href'])
        key = category_key(target)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append({'label': anchor.get_text(' ', strip=True), 'key': key,
                       'url': target.split('/ref=')[0]})
    return result


class Catalog:
    def __init__(self, cache_file, fetch=None):
        self.path = Path(cache_file)
        self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
        self.fetch = fetch or self.fetch_page
        self.lock = threading.RLock()

    @staticmethod
    def fetch_page(url):
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0',
                                              'Accept-Language': 'en-US,en;q=0.9'}, timeout=30)
        response.raise_for_status()
        if urlsplit(response.url).hostname != urlsplit(url).hostname:
            raise ValueError('Amazon 跳转到其他国家站点；请核对所选国家。')
        return response.text, response.url

    def read(self, key, url, parser, refresh=False):
        with self.lock:
            return self._read(key, url, parser, refresh)

    def _read(self, key, url, parser, refresh=False):
        if key not in self.data or refresh:
            html, final_url = self.fetch(url)
            if parser is parse_categories and category_key(url) and category_key(final_url) != category_key(url):
                raise ValueError('分类页面跳转到其他类目；不更新所选类目的选项。')
            items = parser(html, final_url)
            self.data[key] = {'items': items, 'source': final_url,
                              'fetched_at': datetime.now(timezone.utc).isoformat()}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
        return self.data[key]['items']

    def markets(self, refresh=False):
        return self.read('markets', MARKETS_URL, parse_markets, refresh)

    def categories(self, url, refresh=False):
        return self.read(url, url, parse_categories, refresh)

    def invalidate_categories(self, origin):
        # Called only by the explicit refresh button; country choices remain cached.
        self.data = {key: value for key, value in self.data.items() if not key.startswith(origin)}
        if self.path.exists():
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
