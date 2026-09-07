import {parseArgs} from 'node:util';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import path from 'node:path';
import {aggregateDays,mergeHistory} from './sales_windows.mjs';
export function uniqueProducts(items) {
  const seen = new Set();
  return items.filter(p => {
    if (!p.product_id || !p.title?.trim()) return false;
    const key = `${p.platform}:${p.country}:${p.product_id}:${p.variant_id || ''}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

async function post(url, body, key) {
  const response = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json', Authorization:`Bearer ${key}`}, body:JSON.stringify(body), signal:AbortSignal.timeout(45000) });
  if (!response.ok) throw Error(`接口返回 HTTP ${response.status}`);
  const data = await response.json();
  if (data.code !== undefined && data.code !== 0) throw Error(`平台接口错误 ${data.code}`);
  return data;
}

export async function fastmoss(source, config) {
  const key = process.env[source.keyEnv || 'FASTMOSS_API_KEY'];
  if (!key) throw Error('未设置 FastMoss API Key');
  if (!Number.isInteger(source.categoryId) || source.categoryId <= 0) throw Error('请填写该市场玩具类目的 FastMoss 一级类目 ID');
  let products = [];
  for (let page = 1; page <= 50 && products.length < 200; page++) {
    const data = await post('https://openapi.fastmoss.com/product/v1/search', {
      filter:{region:config.country, l1_category_id:source.categoryId, off_shelves:0, ...(source.list === 'new_releases' ? {is_new_listed:true} : {})},
      orderby:[{field:'day7_units_sold',order:'desc'}], page, pagesize:100,
    }, key);
    if (!Array.isArray(data.data?.list)) throw Error('FastMoss 返回中缺少 data.list');
    const batch = data.data.list;
    const before = products.length;
    products = uniqueProducts([...products, ...batch.filter(p => p.region === config.country).map((p, i) => ({
      platform:'tiktok', country:p.region, product_id:p.product_id, title:p.title,
      rank:(page - 1) * 100 + i + 1, rank_scope:'FastMoss 近 7 日销量降序',
      image_url:p.cover, image_scope:'product', brand:null, listed_at:null, rating:null,
      sales_day:null, sales_week:{value:p.day7_units_sold ?? null, days:7, source:'FastMoss search',value_type:'third_party_estimate',scope:'product',window:'平台近 7 日，具体截止时间未返回'}, sales_month:null,
      metric_source:'FastMoss', value_type:'third_party', collected_at:new Date().toISOString(),
      product_url:`https://www.tiktok.com/view/product/${p.product_id}`,
    }))]);
    if (batch.length < 100 || products.length === before) break;
  }
  return {products:products.slice(0,200), note:'FastMoss 近 7 日销量排序；新品筛选使用平台 is_new_listed 定义。不是 TikTok 官方 Best Sellers 排名。'};
}


const {values:a}=parseArgs({options:{country:{type:'string'},category:{type:'string'},list:{type:'string',default:'best_sellers'},output:{type:'string'},'key-env':{type:'string',default:'FASTMOSS_API_KEY'},'sales-history':{type:'string'},'end-date':{type:'string'}}});
try {
  if(!a.country||!a.category||!a.output) throw Error('Required: --country --category --output');
  const result=await fastmoss({categoryId:Number(a.category),list:a.list,keyEnv:a['key-env']},{country:a.country});
  if (a['sales-history']) {
    if (!a['end-date'] || !/^\d{4}-\d{2}-\d{2}$/.test(a['end-date'])) throw Error('销量历史采集需要 --end-date YYYY-MM-DD，按来源完整日期选择');
    const directory=path.resolve(a['sales-history'],a.country);
    await mkdir(directory,{recursive:true});
    for(const product of result.products) {
      try {
        const response=await post('https://openapi.fastmoss.com/product/v1/salesTrend',{filter:{product_id:product.product_id,days:28}},process.env[a['key-env']]);
        if (!Array.isArray(response.data?.list)) throw Error('日销量响应缺少 data.list');
        const file=path.join(directory,`${product.product_id}.json`);
        let old=[];try {old=JSON.parse(await readFile(file,'utf8'));} catch(error) {if(error.code!=='ENOENT') throw error;}
        const rows=mergeHistory(old,response.data.list);
        await writeFile(file,JSON.stringify(rows,null,2));
        product.sales_day=aggregateDays(rows,a['end-date'],1);
        product.sales_week=aggregateDays(rows,a['end-date'],7);
        product.sales_month=aggregateDays(rows,a['end-date'],30);
      } catch(error) {product.sales_error=error.message;}
    }
  }
  await mkdir(path.dirname(path.resolve(a.output)),{recursive:true});
  await writeFile(a.output,JSON.stringify(result,null,2));
  console.log(JSON.stringify({count:result.products.length,output:path.resolve(a.output)}));
} catch(error) {console.error(error.message);process.exitCode=1;}
