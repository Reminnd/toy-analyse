import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from amazon_catalog import Catalog, parse_categories, parse_markets
from settings import execute, validate_scope
from python_crawler import crawl

MARKET = {'country': 'US', 'label': 'United States', 'origin': 'https://www.amazon.com'}
ROOT = {'label': 'Test category', 'key': 'test', 'url': MARKET['origin'] + '/zgbs/test'}
CHILD = {'label': 'Test child', 'key': 'test/123', 'url': ROOT['url'] + '/123'}


def make_cache(workspace):
    def entry(items, source):
        return {'items': items, 'source': source, 'fetched_at': 'fixture'}
    data = {'markets': entry([MARKET], 'https://www.amazon.com/customer-preferences/country'),
            MARKET['origin'] + '/Best-Sellers/zgbs': entry([ROOT], MARKET['origin'] + '/Best-Sellers/zgbs'),
            ROOT['url']: entry([CHILD], ROOT['url']), CHILD['url']: entry([], CHILD['url'])}
    path = Path(workspace) / 'work/product-research-catalog.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data), encoding='utf-8')
    return Catalog(path, fetch=lambda _: (_ for _ in ()).throw(AssertionError('Unexpected fetch')))


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.catalog = make_cache(self.workspace)
        self.values = {'country': 'US', 'category_keys': ['test'], 'schedule_enabled': False,
                       'timezone': 'Asia/Shanghai', 'output_directory': None}

    def tearDown(self):
        self.temp.cleanup()

    def run_action(self, action, values=None):
        return execute(action, values if values is not None else self.values, self.workspace, self.catalog)

    def test_cached_choices_include_parent_itself_and_children(self):
        data = self.run_action('categories')
        self.assertTrue(data['choices'][0]['is_self'])
        self.assertEqual([c['key'] for c in data['choices']], ['test', 'test/123'])
        self.values['category_keys'] = ['test', 'test/123']
        self.assertEqual(len(self.run_action('categories')['choices']), 1)

    def test_save_parent_and_child_generate_different_scoped_sources(self):
        first = self.run_action('save')['config']
        self.assertEqual(first['sources'][0]['url'], ROOT['url'])
        self.values['category_keys'] = ['test', 'test/123']
        second = self.run_action('save')['config']
        self.assertEqual(second['sources'][1]['url'], MARKET['origin'] + '/gp/new-releases/test/123')
        self.assertEqual(self.run_action('plan', {})['sources'], second['sources'])
        self.assertEqual(second['output_directory'], str(self.workspace / 'outputs'))

    def test_wrong_country_category_and_custom_links_are_rejected(self):
        for change in ({'country': 'GB'}, {'category_keys': ['test/123']},
                       {'custom_sources': ['https://www.amazon.co.uk/zgbs/test', MARKET['origin'] + '/gp/new-releases/test']},
                       {'custom_sources': [ROOT['url'], MARKET['origin'] + '/gp/new-releases/other']}):
            with self.assertRaises(ValueError):
                self.run_action('save', {**self.values, **change})
        self.assertFalse((self.workspace / 'product-research.config.json').exists())

    def test_tampered_saved_link_rejected_before_collection(self):
        config = self.run_action('save')['config']
        config['sources'][0]['url'] = MARKET['origin'] + '/zgbs/other'
        (self.workspace / 'product-research.config.json').write_text(json.dumps(config), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.run_action('plan', {})

    def test_native_schedule_is_pending_not_claimed_created(self):
        values = {**self.values, 'schedule_enabled': True, 'time': '19:00'}
        result = self.run_action('save', values)
        self.assertEqual(result['schedule_status'], 'pending_native_tool')
        for change in ({'time': '25:00'}, {'timezone': 'Not/Real'}, {'output_directory': ''}):
            with self.assertRaises(ValueError):
                self.run_action('save', {**values, **change})

    @patch('python_crawler.requests.Session')
    def test_actual_list_redirect_cannot_change_selected_category(self, factory):
        response = Mock(text='<div id="gridItemRoot"></div>', url=MARKET['origin'] + '/zgbs/other')
        factory.return_value.get.return_value = response
        with self.assertRaisesRegex(ValueError, '类目'):
            crawl(ROOT['url'], 'amazon', 'US', scope={'market': MARKET, 'category': ROOT, 'list': 'best_sellers'})

    def test_scope_accepts_real_pagination_ref_but_rejects_list_type(self):
        validate_scope(ROOT['url'] + '/ref=zg_bs_pg_2?pg=2', MARKET, ROOT, 'best_sellers')
        with self.assertRaises(ValueError):
            validate_scope(ROOT['url'], MARKET, ROOT, 'new_releases')


class CatalogTests(unittest.TestCase):
    def test_redirect_to_other_category_is_not_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'cache.json'
            catalog = Catalog(target, lambda _: ('<html></html>', MARKET['origin'] + '/zgbs/other'))
            with self.assertRaisesRegex(ValueError, '其他类目'):
                catalog.categories(ROOT['url'])
            self.assertFalse(target.exists())

    def test_observed_markets_and_direct_children(self):
        markets = parse_markets('<select id="icp-dropdown"><option value="">US</option><option value="https://www.amazon.co.jp/">Japan</option><option value="https://www.amazon.com/">US duplicate</option></select>')
        self.assertEqual([m['country'] for m in markets], ['US', 'JP'])
        html = '<ul class="zg-browse-root"><li><a href="/zgbs">All</a></li><li><ul class="zg-browse-group"><li><span aria-current="page">Parent</span></li><li><ul class="zg-browse-group"><li><a href="/zgbs/test/123/ref=x">Child</a></li></ul></li></ul></li></ul>'
        self.assertEqual(parse_categories(html, MARKET['origin'])[0]['key'], 'test/123')

    def test_cached_data_refreshed_only_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            fetch = Mock(return_value=('<select id="icp-dropdown"><option value="">US</option></select>', 'https://www.amazon.com/'))
            catalog = Catalog(Path(directory) / 'cache.json', fetch)
            catalog.markets(); catalog.markets()
            self.assertEqual(fetch.call_count, 1)
            catalog.markets(True)
            self.assertEqual(fetch.call_count, 2)


if __name__ == '__main__':
    unittest.main()
