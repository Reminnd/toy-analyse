import sys
import time
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from python_crawler import crawl


class SpeedTests(unittest.TestCase):
    def run_collection(self, workers, cache=None, challenge=False):
        lock = threading.Lock()
        state = {'active': 0, 'peak': 0, 'details': 0}
        def get(url, **kwargs):
            if '/dp/' not in url:
                html = ''.join(f'<div id="gridItemRoot"><span class="zg-bdg-text">#{i}</span>'
                               f'<a href="/dp/B{i:09d}">Observed product title {i}</a></div>' for i in range(1, 9))
                return Mock(text=html, url=url)
            with lock:
                state['active'] += 1
                state['details'] += 1
                state['peak'] = max(state['peak'], state['active'])
            time.sleep(.03)
            with lock:
                state['active'] -= 1
            asin = url.rsplit('/', 1)[-1]
            html = '<form action="/errors_page/validateCaptcha"></form>' if challenge else (
                f'<input id="ASIN" value="{asin}"><span id="productTitle">Observed {asin}</span>')
            return Mock(text=html, url=url)
        def session():
            return Mock(get=get, headers={}, cookies={})
        started = time.perf_counter()
        with patch('python_crawler.requests.Session', side_effect=session):
            result = crawl('https://www.amazon.com/zgbs/test', 'amazon', 'US', 8, True,
                           detail_cache=cache, workers=workers)
        return result, state, time.perf_counter() - started

    def test_two_workers_preserve_ranks_and_fields(self):
        serial, _, serial_time = self.run_collection(1)
        parallel, state, parallel_time = self.run_collection(2)
        self.assertEqual(state['peak'], 2)
        fields = lambda result: [(p['product_id'], p['rank'], p['title']) for p in result['products']]
        self.assertEqual(fields(serial), fields(parallel))
        print(f'Controlled latency benchmark: serial={serial_time:.3f}s two_workers={parallel_time:.3f}s')

    def test_cache_skips_details_without_skipping_fresh_list(self):
        cache = {}
        first, _, _ = self.run_collection(2, cache)
        second, state, _ = self.run_collection(2, cache)
        self.assertEqual(state['details'], 0)
        self.assertEqual(first['coverage'], second['coverage'])
        self.assertEqual(len(second['products']), 8)

    def test_challenge_stops_after_in_flight_batch(self):
        result, state, _ = self.run_collection(2, challenge=True)
        self.assertEqual(state['details'], 2)
        self.assertEqual(result['collection_stop']['code'], 'browser_challenge')
        self.assertEqual(len(result['products']), 8)
