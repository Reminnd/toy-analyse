import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from start import start
from collect import collect_python


class StartTests(unittest.TestCase):
    @patch('start.subprocess.run')
    def test_cancel_never_collects(self, run):
        run.return_value = Mock(stdout='{"saved":false}', stderr='')
        self.assertEqual(start(Path('work'), '')['status'], 'cancelled')
        self.assertEqual(run.call_count, 1)

    @patch('start.subprocess.run')
    def test_save_starts_both_sources(self, run):
        run.side_effect = [Mock(stdout='{"saved":true}', stderr=''), Mock(returncode=0), Mock(returncode=0)]
        result = start(Path('work'), '')
        self.assertEqual(result['status'], 'ready_for_analysis')
        self.assertEqual([row['source'] for row in result['outputs']], ['best_sellers', 'new_releases'])

    @patch('collect.subprocess.run')
    @patch('collect.crawl')
    def test_verification_retries_once_and_preserves_snapshot(self, crawl, run):
        stopped = {'products': [{'product_id': 'old'}], 'collection_stop': {'code': 'browser_challenge'}}
        crawl.side_effect = [stopped, stopped]
        run.return_value = Mock(returncode=0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = {'url': 'https://www.amazon.com/zgbs/toys', 'target': 100, 'list': 'best_sellers'}
            config = {'country': 'US', 'marketplace': {}, 'category_path': [{}], 'sources': [source]}
            result = collect_python(source, config, None, root/'best.json', root/'config.json')
            self.assertEqual(run.call_count, 1)
            self.assertEqual(crawl.call_count, 2)
            self.assertTrue((root/'best-before-verification.json').exists())
            self.assertEqual(result['collection_stop']['code'], 'browser_challenge')

    @patch('collect.subprocess.run')
    @patch('collect.crawl')
    def test_close_browser_does_not_retry(self, crawl, run):
        crawl.return_value = {'products': [], 'collection_stop': {'code': 'browser_challenge'}}
        run.return_value = Mock(returncode=2)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = {'url': 'https://www.amazon.com/zgbs/toys', 'target': 100, 'list': 'best_sellers'}
            config = {'country': 'US', 'marketplace': {}, 'category_path': [{}], 'sources': [source]}
            result = collect_python(source, config, None, root/'best.json', root/'config.json')
            self.assertEqual(crawl.call_count, 1)
            self.assertEqual(result['verification_status'], 'cancelled_or_failed')
