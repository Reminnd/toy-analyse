from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sellersprite import normalize,products,trends
from python_crawler import parse_page,PageAccessError


class Response:
    def __init__(self,data): self.data=data
    def raise_for_status(self): pass
    def json(self): return {'code':'OK','data':self.data}


class Session:
    def __init__(self,responses): self.responses=iter(responses); self.calls=[]
    def request(self,method,url,**kwargs):
        self.calls.append((method,url,kwargs))
        return Response(next(self.responses))


def row(i):
    return {'asin':f'B{i:09d}','title':'Fixture toy','nodeIdPath':'165793011:166027011',
            'bsr':i+1,'units':300,'amzUnit':200,'availableDate':1721779200000}


class SellerSpriteTests(unittest.TestCase):
    def test_parent_and_child_sales_keep_distinct_scope_and_month(self):
        p=normalize(row(1),'US','https://www.amazon.com','202602')
        self.assertEqual(p['sales_month']['scope'],'parent_asin')
        self.assertEqual(p['sales_month']['period_end'],'2026-02-28')
        self.assertEqual(p['child_sales_30d']['scope'],'child_asin')
        self.assertIsNone(p['sales_day'])
        self.assertEqual(p['listed_at'],'2024-07-24T00:00:00+00:00')

    def test_duplicate_api_rows_do_not_fulfill_200_and_category_filter_is_sent(self):
        session=Session([{'items':[row(i) for i in range(100)],'total':200},
                         {'items':[row(i) for i in range(50,150)],'total':200}])
        result=products(session,'US','165793011','https://www.amazon.com')
        self.assertEqual(result['coverage']['actual'],150)
        self.assertEqual(result['coverage']['missing'],50)
        self.assertEqual(session.calls[0][2]['json']['nodeIdPaths'],['165793011'])
        self.assertEqual(session.calls[0][2]['json']['order'],{'field':'bsr_rank','desc':False})

    def test_wrong_market_trend_is_rejected(self):
        session=Session([{'marketplace':'JP','keyword':'toy','items':[]}])
        with self.assertRaises(ValueError): trends(session,'US','toy')

    def test_challenge_and_login_are_not_empty_successes(self):
        cases=[('temu','<script src="upload-static/assets/chl/js/x.js">challenge</script>','browser_challenge'),
               ('aliexpress','<script>localStorage.x5referer; location="https://login.aliexpress.com"</script>','login_required')]
        for platform,html,code in cases:
            with self.assertRaises(PageAccessError) as caught:
                parse_page(html,'https://example.com',platform,'US')
            self.assertEqual(caught.exception.code,code)


if __name__=='__main__': unittest.main()
