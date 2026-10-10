import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from report_visuals import dashboard
from report import render, sales_display, monthly_sales_value


class VisualReportTests(unittest.TestCase):
    def test_monthly_sales_sort_does_not_mix_windows_or_missing(self):
        self.assertEqual(monthly_sales_value('1.5K+ bought in past month'),1500)
        self.assertEqual(monthly_sales_value('700+ bought in past month'),700)
        self.assertEqual(monthly_sales_value('2K+ bought in past week'),'')
        self.assertEqual(monthly_sales_value(None),'')

    def test_sales_display_preserves_lower_bound_and_source_period(self):
        self.assertEqual(sales_display('7K+ bought in past month'),'7K+（月）')
        self.assertEqual(sales_display('200+ bought in past week'),'200+（周）')
        self.assertEqual(sales_display(None),'—（缺失）')
        self.assertEqual(sales_display('100 sold'),'100 sold（周期未识别）')

    def test_keywords_are_not_truncated_and_duplicates_count_once(self):
        terms=[{'en':f'term {i}','zh':f'词{i}','category':'play'} for i in range(35)]
        result=dashboard([{'id':'a','title':'Toy','keywords':terms+[terms[0]]}])
        self.assertIn('35 个归一化关键词',result)
        self.assertIn('35 次商品关联',result)
        self.assertIn('data-keyword="term 34"',result)
        self.assertIn('词0 · 1',result)
        self.assertIn('100.0%',result)

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
