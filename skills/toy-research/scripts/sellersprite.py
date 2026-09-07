"""SellerSprite official API client; preserves source windows and ranking scope."""
import argparse
import calendar
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import requests


def request(session, route, payload, method='POST'):
    response=session.request(method,'https://api.sellersprite.com'+route,
                             **({'params':payload} if method=='GET' else {'json':payload}),timeout=45)
    response.raise_for_status()
    body=response.json()
    if body.get('code') != 'OK':
        raise ValueError('SellerSprite API error: '+str(body.get('code')))
    return body['data']


def metric(value, scope, month=None):
    if not isinstance(value,(int,float)) or value < 0:
        return None
    start=end=None
    if month:
        date=datetime.strptime(month,'%Y%m')
        start=f'{date.year:04d}-{date.month:02d}-01'
        end=f'{date.year:04d}-{date.month:02d}-{calendar.monthrange(date.year,date.month)[1]}'
    return {'value':value,'source':'SellerSprite product/research','value_type':'third_party_estimate',
            'scope':scope,'period_start':start,'period_end':end,
            'window':'calendar_month' if month else 'API 默认窗口，未明确起止日期'}


def normalize(row, marketplace, site_url, month):
    date=row.get('availableDate')
    child=metric(row.get('amzUnit'),'child_asin')
    if child:
        child.update({'window':'平台子体近 30 日','updated_at_source':row.get('amzUnitDate')})
    return {'platform':'amazon','country':marketplace,'product_id':row['asin'],'parent_id':row.get('parent'),
            'title':row['title'],'brand':row.get('brand'),'image_url':row.get('imageUrl'),'image_scope':'asin',
            'variant_attributes':row.get('sku'),'product_url':site_url.rstrip('/')+'/dp/'+row['asin'],
            'rank':row.get('bsr'),'rank_category':row.get('bsrId'),'rank_scope':'SellerSprite 大类 BSR 快照',
            'category_path':row.get('nodeIdPath'),'rating':row.get('rating'),'rating_count':row.get('ratings'),
            'listed_at':datetime.fromtimestamp(date/1000,timezone.utc).isoformat() if isinstance(date,(int,float)) and date>0 else None,
            'listed_at_raw':date,'sales_month':metric(row.get('units'),'parent_asin',month),
            'child_sales_30d':child,'sales_day':None,'sales_week':None,
            'metric_source':'SellerSprite','collected_at':datetime.now(timezone.utc).isoformat()}


def products(session, marketplace, category, site_url, month=None, new_releases=False, limit=200):
    found,seen,pages=[],set(),[]
    error=None
    for page in range(1,21):
        payload={'marketplace':marketplace,'nodeIdPaths':[category],'nodeIdPathEqual':False,
                 'minBsr':1,'maxBsr':200,'variation':'Y','page':page,'size':100,
                 'order':{'field':'bsr_rank','desc':False}}
        if month: payload['month']=month
        if new_releases: payload['badgeNR']='Y'
        try:
            data=request(session,'/v1/product/research',payload)
            rows=data['items']
            if not isinstance(rows,list): raise ValueError('API data.items 不是列表')
        except (requests.RequestException,ValueError,KeyError) as failure:
            if not found: raise
            error=str(failure)
            break
        before=len(found)
        pages.append({'page':page,'items':len(rows),'total':data.get('total')})
        for row in rows:
            asin=row.get('asin')
            row_path=str(row.get('nodeIdPath',''))
            if row_path!=category and not row_path.startswith(category+':'):
                continue
            if not asin or asin in seen or not row.get('title'):
                continue
            if not isinstance(row.get('bsr'),(int,float)) or not 1<=row['bsr']<=200:
                continue
            seen.add(asin)
            found.append(normalize(row,marketplace,site_url,month))
        total=data.get('total')
        if len(found)>=limit or len(rows)<100 or len(found)==before or isinstance(total,int) and page*100>=total:
            break
    found=found[:limit]
    return {'products':found,'pages':pages,'pagination_error':error,'query':{'marketplace':marketplace,'category':category,'month':month},
            'coverage':{'actual':len(found),'target':limit,'missing':max(0,limit-len(found))},
            'note':('新品标识筛选后的大类 BSR 排序，不是 Amazon 官方 New Releases 排名。' if new_releases else '第三方 BSR 快照，不与不同时间的官方榜单无条件拼接。')}


def trends(session, marketplace, keyword):
    data=request(session,'/v1/google/trends',{'marketplace':marketplace,'keyword':keyword,'googleProp':'web','monthly':'false'},'GET')
    if data.get('marketplace') != marketplace or data.get('keyword') != keyword:
        raise ValueError('趋势响应市场或关键词与请求不一致')
    if not isinstance(data.get('items'),list): raise ValueError('趋势响应缺少 items')
    return {'source':'Google Trends via SellerSprite','region':marketplace,'keyword':keyword,
            'url':data.get('link'),'series':data['items'],'search_type':'web',
            'note':'相对兴趣指数，查询窗口以返回链接为准；不能作为绝对搜索量或销量。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key-env',default='SELLERSPRITE_API_KEY')
    parser.add_argument('--output',required=True)
    commands=parser.add_subparsers(dest='command',required=True)
    product=commands.add_parser('products')
    product.add_argument('--marketplace',required=True)
    product.add_argument('--category',required=True,help='真实类目节点路径，以冒号分隔')
    product.add_argument('--site-url',required=True,help='与目标市场一致的 Amazon 站点根 URL')
    product.add_argument('--month')
    product.add_argument('--new-releases',action='store_true')
    trend=commands.add_parser('trends')
    trend.add_argument('--marketplace',required=True)
    trend.add_argument('--keyword',required=True)
    review=commands.add_parser('reviews')
    review.add_argument('--marketplace',required=True)
    review.add_argument('--asin',required=True)
    review.add_argument('--page',type=int,default=1)
    args=parser.parse_args()
    try:
        key=os.environ.get(args.key_env)
        if not key: raise ValueError('未设置凭证环境变量 '+args.key_env)
        session=requests.Session()
        session.headers.update({'secret-key':key,'Content-Type':'application/json'})
        if args.command=='products':
            if args.month: datetime.strptime(args.month,'%Y%m')
            result=products(session,args.marketplace,args.category,args.site_url,args.month,args.new_releases)
        elif args.command=='trends':
            result=trends(session,args.marketplace,args.keyword)
        else:
            data=request(session,'/v1/review',{'marketplace':args.marketplace,'asin':args.asin,'page':args.page,'size':10})
            result={'source':'SellerSprite review','marketplace':args.marketplace,'asin':args.asin,'page':args.page,
                    'raw_data':data,'note':'响应原文，需根据实际结构提取评论 ID 与内容；未假设未公开的响应封装。'}
        output=Path(args.output)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'output':str(output),'command':args.command}))
        return 0
    except (ValueError,KeyError,OSError,requests.RequestException) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False))
        return 1


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
