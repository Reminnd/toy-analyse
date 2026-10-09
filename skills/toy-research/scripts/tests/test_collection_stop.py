import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from python_crawler import crawl, parse_page, PageAccessError


BASE = 'https://www.amazon.com'
CHALLENGE = '<form action="/errors_page/validateCaptcha"></form>'


def response(html, url):
    return Mock(text=html, url=url)


def card(rank):
    return (f'<div id="gridItemRoot"><span class="zg-bdg-text">#{rank}</span>'
            f'<a href="/dp/B00000000{rank}">A rendered toy title {rank}</a></div>')


class CollectionStopTests(unittest.TestCase):
    @patch('python_crawler.requests.Session')
    def test_embedded_challenge_keeps_loaded_records_and_stops_requests(self, factory):
        embedded = json.dumps([{'id': f'B00000000{rank}',
                               'metadataMap': {'render.zg.rank': str(rank)}} for rank in [2, 3]])
        html = card(1) + f"<div data-client-recs-list='{embedded}'></div>"
        html += '<li class="a-last"><a href="/page2">Next</a></li>'
        session = factory.return_value
        session.get.side_effect = [response(html, BASE+'/list'), response(CHALLENGE, BASE+'/dp/B000000002')]
        result = crawl(BASE+'/list', 'amazon', 'US', 100, details=True)
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(len(result['products']), 1)
        self.assertEqual([p['rank'] for p in result['unresolved_products']], [2, 3])
        self.assertIn('error', result['unresolved_products'][0])
        self.assertIn('deferred_reason', result['unresolved_products'][1])
        self.assertEqual(result['collection_stop']['phase'], 'embedded_detail')
        self.assertEqual(result['next_page'], BASE+'/page2')
        self.assertIsNone(result['coverage']['source_range_shortfall'])
        self.assertEqual(result['coverage']['missing_declared_ranks'], [2, 3])

    @patch('python_crawler.requests.Session')
    def test_detail_challenge_preserves_success_and_marks_unrequested_details(self, factory):
        session = factory.return_value
        session.get.side_effect = [response(''.join(card(n) for n in [1, 2, 3]), BASE+'/list'),
            response('<input id="ASIN" value="B000000001"><span id="productTitle">Toy one</span>', BASE+'/dp/B000000001'),
            response(CHALLENGE, BASE+'/dp/B000000002')]
        result = crawl(BASE+'/list', 'amazon', 'US', 100, details=True)
        self.assertEqual(session.get.call_count, 3)
        self.assertEqual(len(result['products']), 3)
        self.assertTrue(result['products'][0]['detail_source'])
        self.assertIn('detail_error', result['products'][1])
        self.assertNotIn('detail_error', result['products'][2])
        self.assertIn('detail_deferred_reason', result['products'][2])
        self.assertEqual(result['collection_stop']['product_id'], 'B000000002')

    @patch('python_crawler.requests.Session')
    def test_zero_titled_products_still_returns_declared_gap_evidence(self, factory):
        embedded = json.dumps([{'id': 'B000000001', 'metadataMap': {'render.zg.rank': '1'}}])
        factory.return_value.get.side_effect = [response(f"<div data-client-recs-list='{embedded}'></div>", BASE+'/list'),
                                               response(CHALLENGE, BASE+'/dp/B000000001')]
        result = crawl(BASE+'/list', 'amazon', 'US', 100)
        self.assertEqual(result['products'], [])
        self.assertEqual(result['coverage']['actual'], 0)
        self.assertEqual(result['unresolved_products'][0]['product_id'], 'B000000001')
        self.assertEqual(result['collection_stop']['code'], 'browser_challenge')

    def test_list_challenge_is_not_an_empty_success(self):
        with self.assertRaises(PageAccessError) as caught:
            parse_page(CHALLENGE, BASE+'/list', 'amazon', 'US')
        self.assertEqual(caught.exception.code, 'browser_challenge')
