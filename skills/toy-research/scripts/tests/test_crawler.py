import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from python_crawler import parse_page
from amazon_detail import parse_detail
from session_state import load_state


class CrawlerTests(unittest.TestCase):
    def test_price_comparison_ignores_unit_price_and_credit_offer(self):
        html = '''<input id="ASIN" value="B000000001"><span id="productTitle">Toy</span>
        <div id="corePriceDisplay_desktop_feature_div">
        <span class="priceToPay"><span class="a-price-symbol">$</span><span class="a-price-whole">13.</span><span class="a-price-fraction">99</span></span>
        <span class="basisPrice">List Price: <span class="a-text-price"><span class="a-offscreen">$19.99</span></span></span>
        <span class="apex-priceperunit-value">$0.99 / count</span></div><div>Credit offer $0.00</div>'''
        price = parse_detail(html,'https://www.amazon.com/dp/B000000001','B000000001')['pricing']
        self.assertEqual(price['current_price'],13.99)
        self.assertEqual(price['reference_price'],19.99)
        self.assertEqual(price['currency'],'USD')
        self.assertAlmostEqual(price['discount_percent'],30.02)

    def test_gallery_requires_matching_current_main_image(self):
        images = [{'hiRes':'https://m.media-amazon.com/images/I/main._SL1500_.jpg','variant':'MAIN'},
                  {'hiRes':'https://m.media-amazon.com/images/I/side._SL1500_.jpg','variant':'PT01'}]
        html = '<input id="ASIN" value="B000000001"><span id="productTitle">Toy</span>'
        html += '<img id="landingImage" src="https://m.media-amazon.com/images/I/main._SX400_.jpg">'
        html += "<script>var data={'colorImages': { 'initial': A.$.parseJSON('"+json.dumps(images)+"')}};</script>"
        result = parse_detail(html,'https://www.amazon.com/dp/B000000001','B000000001')
        self.assertEqual(len(result['gallery']),2)
        self.assertEqual(result['gallery'][1]['asin'],'B000000001')
        mismatched = html.replace('/main._SX400_', '/other._SX400_')
        self.assertEqual(parse_detail(mismatched,'https://www.amazon.com/dp/B000000001','B000000001')['gallery'],[])

    def test_feature_bullets_are_scoped_and_deduplicated(self):
        html = '''<input id="ASIN" value="B000000001"><span id="productTitle">Toy</span>
        <div id="feature-bullets"><ul><li><span class="a-list-item">Portable play</span></li>
        <li><span class="a-list-item">Portable play</span></li></ul></div>
        <div><span class="a-list-item">Unrelated recommendation</span></div>'''
        result = parse_detail(html, 'https://www.amazon.com/dp/B000000001', 'B000000001')
        self.assertEqual(result['feature_bullets'], ['Portable play'])

    def test_embedded_ids_keep_source_rank_without_inventing_title(self):
        records=[{'id':'B000000031','metadataMap':{'render.zg.rank':'31'}}]
        html='<div data-client-recs-list=\''+json.dumps(records)+'\'></div>'
        product=parse_page(html,'https://www.amazon.com/zgbs','amazon','US')['products'][0]
        self.assertEqual(product['rank'],31)
        self.assertEqual(product['title'],'')
        self.assertTrue(product['needs_detail'])

    def test_detail_does_not_use_first_seen_as_listing_date(self):
        html='''<input id="ASIN" value="B000000001"><span id="productTitle">A toy</span>
        <div id="productOverview_feature_div"><table><tr><td>Brand</td><td>Example</td></tr></table></div>
        <span id="social-proofing-faceout-title-tk_bought">1K+ bought in past month</span>
        <div data-hook="review" id="r1"><div data-hook="reviewRichContentContainer">Not durable</div></div>'''
        result=parse_detail(html,'https://www.amazon.com/dp/B000000001','B000000001')
        self.assertEqual(result['brand'],'Example')
        self.assertIsNone(result['listed_at'])
        self.assertEqual(result['displayed_sales_message'],'1K+ bought in past month')
        self.assertEqual(result['reviews'][0]['text'],'Not durable')
        with self.assertRaises(ValueError): parse_detail(html,'https://www.amazon.com','B000000002')

    def test_snapshot_skips_expired_and_unrelated_cookies_and_respects_path(self):
        state={'cookies':[
            {'name':'session','value':'test-session','domain':'.example.com','path':'/private','secure':True,'expires':time.time()+1000},
            {'name':'expired','value':'old','domain':'.example.com','expires':1},
            {'name':'unrelated','value':'other','domain':'.elsewhere.com','expires':-1},
        ]}
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'state.json'
            file.write_text(json.dumps(state),encoding='utf-8')
            session=requests.Session()
            info=load_state(session,file,'https://www.example.com/private')
            self.assertEqual(info['loaded_cookie_count'],1)
            self.assertEqual(info['expired_cookie_count'],1)
            allowed=session.prepare_request(requests.Request('GET','https://www.example.com/private/items'))
            public=session.prepare_request(requests.Request('GET','https://www.example.com/public'))
            other=session.prepare_request(requests.Request('GET','https://www.elsewhere.com/private'))
            insecure=session.prepare_request(requests.Request('GET','http://www.example.com/private'))
            self.assertEqual(allowed.headers.get('Cookie'),'session=test-session')
            for request in [public,other,insecure]: self.assertNotIn('Cookie',request.headers)

    def test_detail_reads_explicit_byline_brand_and_aggregate_rating(self):
        html='''<input id="ASIN" value="B0H7PWTPTV"><span id="productTitle">Coconut Oil Squishy</span>
        <a id="bylineInfo">Brand: LAVKUHY</a><span id="acrPopover" title="3.6 out of 5 stars"></span>
        <span id="acrCustomerReviewText">245 ratings</span><div id="productOverview_feature_div"></div>'''
        result=parse_detail(html,'https://www.amazon.com/dp/B0H7PWTPTV','B0H7PWTPTV')
        self.assertEqual(result['brand'],'LAVKUHY')
        self.assertEqual(result['rating'],3.6)
        self.assertEqual(result['rating_count'],245)
        self.assertIsNone(result['review_count'])
        self.assertIsNone(result['listed_at'])
        result=parse_detail(html.replace('Brand: LAVKUHY','Visit the LAVKUHY Store'),'https://www.amazon.com','B0H7PWTPTV')
        self.assertIsNone(result['brand'])

    def test_continue_shopping_page_is_reported_as_verification(self):
        html='<title>Amazon.com</title><form action="/errors_page/validateCaptcha"><button>Continue shopping</button></form>'
        with self.assertRaisesRegex(ValueError,'继续购物验证页面'):
            parse_detail(html,'https://www.amazon.com/dp/B09PGVGCH5','B09PGVGCH5')

    def test_expanded_details_and_selected_asin_image(self):
        html='''<input id="ASIN" value="B0H7PWTPTV"><span id="productTitle">Squishy</span>
        <div id="productDetails_expanderTables_depthLeftSections"><table><tr><th>Brand Name</th><td>LAVKUHY</td></tr></table></div>
        <img id="landingImage" src="https://example.com/small.jpg" data-old-hires="https://example.com/large.jpg">
        <div data-hook="review" id="empty"><div data-hook="review-body"> </div></div>'''
        result=parse_detail(html,'https://www.amazon.com/dp/B0H7PWTPTV','B0H7PWTPTV')
        self.assertEqual(result['brand'],'LAVKUHY')
        self.assertEqual(result['image_asin'],'B0H7PWTPTV')
        self.assertEqual(result['image_scope'],'selected_asin')
        self.assertEqual(result['image_url'],'https://example.com/large.jpg')
        self.assertEqual(result['reviews'],[])
        result=parse_detail(html.replace('id="ASIN"','id="other"'),'https://www.amazon.com','B0H7PWTPTV')
        self.assertIsNone(result['image_asin'])
        self.assertEqual(result['image_scope'],'product')


if __name__=='__main__': unittest.main()
