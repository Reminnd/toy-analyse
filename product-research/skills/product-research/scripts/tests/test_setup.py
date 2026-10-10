import json
import sys
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from amazon_catalog import Catalog, parse_categories, parse_markets
from setup import SetupWindow, build_config

MARKET = {'country': 'US', 'label': 'United States', 'origin': 'https://www.amazon.com'}
PARENT = {'label': 'Home & Kitchen', 'key': 'home-garden', 'url': MARKET['origin'] + '/zgbs/home-garden'}
CHILD = {'label': 'Bedding', 'key': 'home-garden/123', 'url': PARENT['url'] + '/123'}
URLS = [PARENT['url'], MARKET['origin'] + '/gp/new-releases/' + PARENT['key']]


class CatalogTests(unittest.TestCase):
    def test_markets_are_observed_deduplicated_not_preset(self):
        html = '<select id="icp-dropdown"><option value="">United States</option><option value="https://www.amazon.co.jp/">Japan</option><option value="https://www.amazon.com/">US again</option></select>'
        self.assertEqual([m['country'] for m in parse_markets(html)], ['US', 'JP'])

    def test_tree_does_not_mix_ancestors_and_siblings(self):
        html = '''<ul class="zg-browse-root"><li><a href="/zgbs">All</a></li><li><span><ul class="zg-browse-group">
        <li><span aria-current="page">Home</span></li><li><span><ul class="zg-browse-group">
        <li><span><a href="/zgbs/home/1/ref=x">Bedding</a></span></li>
        <li><span><a href="/zgbs/home/2/ref=y">Bath</a></span></li></ul></span></li></ul></span></li></ul>'''
        self.assertEqual([c['key'] for c in parse_categories(html, MARKET['origin'])], ['home/1', 'home/2'])
        self.assertEqual(parse_categories('<ul class="zg-browse-root"><li><span aria-current="page">Leaf</span></li></ul>', MARKET['origin']), [])

    def test_cache_skips_network_until_explicit_refresh(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return '<select id="icp-dropdown"><option value="">US</option></select>', url
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / 'cache.json'
            catalog = Catalog(filename, fetch)
            catalog.markets()
            Catalog(filename, fetch).markets()
            self.assertEqual(len(calls), 1)
            catalog.markets(refresh=True)
            self.assertEqual(len(calls), 2)
            self.assertIn('fetched_at', json.loads(filename.read_text())['markets'])

    def test_error_is_not_cached_as_empty_success(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / 'cache.json'
            catalog = Catalog(filename, lambda url: ('<html>challenge</html>', url))
            with self.assertRaises(ValueError):
                catalog.markets()
            self.assertFalse(filename.exists())


class ConfigTests(unittest.TestCase):
    def test_schedule_and_country_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            for time_text in ('', '25:00', '19:60'):
                with self.assertRaises(ValueError):
                    build_config({}, MARKET, [PARENT], URLS, True, time_text, 'Asia/Shanghai', directory)
            with self.assertRaises(ValueError):
                build_config({}, MARKET, [PARENT], URLS, True, '19:00', 'Unknown/Timezone', directory)
            with self.assertRaises(ValueError):
                build_config({}, MARKET, [PARENT], [URLS[0], 'https://www.amazon.co.jp/zgbs'], False, '', '', directory)
            previous = {'country': 'JP', 'storage_state': 'private.json', 'delivery': {'postal_code': 'example'}}
            config = build_config(previous, MARKET, [PARENT], URLS, False, '', '', directory)
            self.assertNotIn('storage_state', config)
            self.assertNotIn('delivery', config)
            self.assertFalse(config['schedule_enabled'])
            self.assertFalse(config['supplemental_sources_allowed'])


class FakeCatalog:
    def markets(self, refresh=False):
        return [MARKET]

    def categories(self, url):
        if url.endswith('/Best-Sellers/zgbs'):
            return [PARENT]
        if url == PARENT['url']:
            return [CHILD]
        return []


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self.directory.cleanup()

    def settle(self, app):
        deadline = time.monotonic() + 3
        while app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.02)
        self.assertFalse(app.busy)

    def test_parent_child_directory_and_saved_choices(self):
        app = SetupWindow(self.root, self.directory.name, 'Asia/Shanghai', FakeCatalog())
        self.settle(app)
        self.assertEqual(app.country.current(), -1)
        app.country.current(0)
        app.select_market()
        self.settle(app)
        app.levels[0][0].current(0)
        app.select_category(0)
        self.settle(app)
        self.assertEqual(app.path, [PARENT])
        app.levels[1][0].current(1)
        app.select_category(1)
        self.settle(app)
        self.assertEqual(app.path, [PARENT, CHILD])
        app.levels[1][0].current(0)
        app.select_category(1)
        self.assertEqual(app.path, [PARENT])
        output = Path(self.directory.name) / '客户 报告'
        output.mkdir()
        app.default_output.set(False)
        app.toggle_output()
        with patch('setup.filedialog.askdirectory', return_value=str(output)):
            app.browse()
        app.scheduled.set(True)
        app.toggle_schedule()
        app.time.set('19:00')
        app.save()
        config = json.loads(app.config_path.read_text(encoding='utf-8'))
        self.assertEqual(config['output_directory'], str(output))
        self.assertTrue(config['schedule_enabled'])
        self.assertEqual(config['time'], '19:00')
        self.assertEqual(config['sources'][1]['url'], URLS[1])

    def test_reopen_restores_custom_links_at_leaf_and_cancel_keeps_file(self):
        urls = [URLS[0] + '?custom=1', URLS[1] + '?custom=1']
        config = build_config({}, MARKET, [PARENT, CHILD], urls, False, '', 'Asia/Shanghai', self.directory.name)
        path = Path(self.directory.name) / 'product-research.config.json'
        original = json.dumps(config)
        path.write_text(original, encoding='utf-8')
        app = SetupWindow(self.root, self.directory.name, catalog=FakeCatalog())
        self.settle(app)
        self.assertEqual(app.path, [PARENT, CHILD])
        self.assertTrue(app.custom.get())
        self.assertEqual([v.get() for v in app.urls], urls)
        self.assertEqual(path.read_text(encoding='utf-8'), original)
        self.assertFalse(app.saved)


if __name__ == '__main__':
    unittest.main()
