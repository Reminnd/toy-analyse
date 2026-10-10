import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from report_visuals import dashboard
from report import render


class VisualReportTests(unittest.TestCase):
    def test_price_median_uses_known_usd_and_terms_count_products(self):
        items = [{'id':str(i),'title':'Building Toy','brand':'Example',
                  'pricing':{'current_price':price,'currency':currency},
                  'keywords':[{'en':'building toy','zh':'拼搭玩具'}]}
                 for i,(price,currency) in enumerate([(10,'USD'),(30,'USD'),(999,'EUR')])]
        result = dashboard(items)
        self.assertIn('$20.00',result)
        self.assertIn('USD 有效样本 2 个',result)
        self.assertIn('拼搭玩具 · 3',result)
        self.assertIn('没有同时取得当前售价和更高参考价',result)

    def test_gallery_and_price_comparison_render_with_scope(self):
        result = render({'products':[{'id':'p','title':'Toy',
            'pricing':{'current_price':10,'reference_price':20,'currency':'USD',
                       'reference_label':'List Price','discount_percent':50},
            'gallery':[{'url':'https://example.com/image.jpg','image_role':'MAIN','asin':'p'}]}]})
        self.assertIn('参考价 <del>20.00</del>',result)
        self.assertIn('class="product-gallery"',result)
        self.assertIn('id="gallery-dialog"',result)
        self.assertIn('data-product',result)
