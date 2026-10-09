import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from report import render, validate


class ReportTests(unittest.TestCase):
    def test_detail_specs_and_summary_are_visible_when_supplied(self):
        result = render({'products': [{'id':'p','title':'Toy',
            'specifications':{'Material':'Clay'},'feature_summary':'页面介绍便携玩法。'}]})
        self.assertIn('<dt>Material</dt><dd>Clay</dd>', result)
        self.assertIn('页面介绍便携玩法。', result)
        self.assertIn('展开详情规格与商品要点', result)

    def test_cross_list_product_counts_once_toward_global_target(self):
        result = render({'unique_product_target': 200,
            'sources': [{'name': 'Best', 'count': 1}, {'name': 'New', 'count': 1}],
            'products': [{'id': 'amazon:US:B000000001', 'title': 'Toy',
                          'sources': ['Best', 'New']}]})
        self.assertIn('实际 1 个；缺口 199 个', result)

    def test_duplicate_asin_with_different_ids_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ASIN 重复'):
            validate({'country': 'US', 'products': [
                {'id': 'best:a', 'platform': 'amazon', 'product_id': 'B000000001'},
                {'id': 'new:a', 'platform': 'amazon', 'product_id': 'B000000001'}]})

    def test_source_sales_and_bilingual_terms_are_visible(self):
        result = render({'products': [{'id': 'p', 'title': 'Toy',
            'displayed_sales_message': '10K+ bought in past month',
            'keywords': [{'en': 'latex balloons', 'zh': '乳胶气球'}]}]})
        self.assertIn('10K+ bought in past month', result)
        self.assertIn('latex balloons / 乳胶气球', result)
        self.assertNotIn('<th>日销量</th>', result)
        self.assertNotIn('<th>周销量</th>', result)
        self.assertNotIn('<th>月销量</th>', result)

    def test_missing_translation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '中文 zh'):
            validate({'products': [{'id': 'p', 'keywords': [{'en': 'balloons'}]}]})
