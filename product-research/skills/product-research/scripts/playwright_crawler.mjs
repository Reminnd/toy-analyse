import { chromium } from 'playwright';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { readAmazonDetail } from './amazon_detail.mjs';
import { recoverAmazon } from './amazon_recovery.mjs';
import { validateSourceScope } from './source_scope.mjs';
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

export async function website(source, config, root, progress) {
  if (!source.url) throw Error('未配置原站链接，不能执行网页备选采集');
  if (['sellersprite','selection_assistant'].includes(source.platform)) throw Error('该卖家平台尚未完成页面字段适配，请提供准确产品链接及可用 API 文档');
  if (source.platform === 'google_trends') throw Error('Google Trends 趋势接口尚未接入；不会将搜索兴趣伪装成商品销量或榜单');
  const profile = path.join(root, 'profiles', `${source.platform}-${config.country}`);
  await mkdir(profile, {recursive:true});
  const browserOptions = {
    channel: config.browser === 'chromium' ? undefined : config.browser,
    headless:true,
  };
  let browser;
  let context;
  if (source.storageState) {
    const state=JSON.parse(await readFile(source.storageState,'utf8'));
    browser=await chromium.launch(browserOptions);
    context=await browser.newContext({storageState:{cookies:state.cookies,origins:state.origins},userAgent:state.user_agent,locale:'en-US',viewport:{width:1360,height:900}});
  } else {
    context=await chromium.launchPersistentContext(profile,{...browserOptions,locale:'en-US',viewport:{width:1360,height:900}});
  }
  const page = await context.newPage();
  let products = [], observedDelivery = '', visited = new Set();
  try {
    if (source.pythonResult) {
      const original = JSON.parse(await readFile(source.pythonResult, 'utf8'));
      return await recoverAmazon(page, original, source, config.country, progress);
    }
    await page.goto(source.url, {waitUntil:'domcontentloaded',timeout:45000});
    for (let pageNo = 1; pageNo <= 20 && products.length < (source.limit || 200); pageNo++) {
      validateSourceScope(page.url(), source);
      if (visited.has(page.url())) break;
      visited.add(page.url());
      progress(`读取 ${source.name || source.platform} 第 ${pageNo} 页`);
      let stableBottom = 0;
      for (let scroll = 0; scroll < 40 && stableBottom < 3; scroll++) {
        await page.evaluate(() => window.scrollBy(0, 850));
        await page.waitForTimeout(450);
        const atBottom = await page.evaluate(() => window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 5);
        stableBottom = atBottom ? stableBottom + 1 : 0;
      }
      const extracted = await page.evaluate(({platform,country}) => {
        const safeURL = value => {
          try { const u = new URL(value, location.href); return ['https:','http:'].includes(u.protocol) ? u.href : null; } catch { return null; }
        };
        if (platform === 'amazon') {
          const cards = [...document.querySelectorAll('[id="gridItemRoot"], .zg-item-immersion')];
          const items = cards.map(card => {
            const links = [...card.querySelectorAll('a[href*="/dp/"]')];
            const link = links.find(a => a.textContent.trim().length > 15) || links[0];
            const product_id = link?.href.match(/\/dp\/([A-Z0-9]{10})/)?.[1];
            const image = card.querySelector('img');
            const ratingText = card.querySelector('.a-icon-alt')?.textContent || '';
            return { platform, country, product_id,
              title:link?.textContent.trim() || image?.alt || '',
              rank:Number(card.querySelector('.zg-bdg-text')?.textContent.replace(/\D/g,'')) || null,
              product_url:safeURL(link?.href), image_url:safeURL(image?.src), image_scope:'product',
              rating:ratingText ? Number(ratingText.match(/[0-9]+[.,]?[0-9]*/)?.[0]?.replace(',','.')) || null : null,
              rating_raw:ratingText, brand:null, listed_at:null,
              sales_day:null,sales_week:null,sales_month:null, metric_source:null,
            };
          });
          const next = document.querySelector('li.a-last a');
          return {items, next:next?.href, delivery:document.querySelector('#glow-ingress-block')?.innerText || '', title:document.title};
        }
        // Public Product structured data is a first extraction path. Missing markup
        // is reported, never replaced with fabricated product records or rankings.
        const items = [];
        function visit(value) {
          if (!value || typeof value !== 'object') return;
          if (Array.isArray(value)) { value.forEach(visit); return; }
          const types = [].concat(value['@type'] || []);
          if (types.includes('Product')) {
            const productURL = safeURL(value.url);
            const id = value.productID || value.sku || productURL;
            items.push({platform,country,product_id:String(id || ''),title:value.name || '',rank:null,rank_scope:'未取得榜单排名',
              product_url:productURL,image_url:safeURL([].concat(value.image || [])[0]), image_scope:'product',
              brand:typeof value.brand === 'string' ? value.brand : value.brand?.name || null,
              rating:value.aggregateRating?.ratingValue ?? null, review_count:value.aggregateRating?.reviewCount ?? null,
              listed_at:null,sales_day:null,sales_week:null,sales_month:null});
          }
          Object.values(value).forEach(visit);
        }
        document.querySelectorAll('script[type="application/ld+json"]').forEach(el => {try {visit(JSON.parse(el.textContent));} catch {}});
        return {items,next:document.querySelector('a[rel="next"]')?.href,title:document.title,delivery:''};
      }, {platform:source.platform,country:config.country});
      observedDelivery = extracted.delivery || observedDelivery;
      const before = products.length;
      products = uniqueProducts([...products,...extracted.items.map(p => ({...p,collected_at:new Date().toISOString()}))]);
      await mkdir(path.join(root,'evidence'),{recursive:true});
      await writeFile(path.join(root,'evidence',`${source.id}-${pageNo}.json`), JSON.stringify({url:page.url(),...extracted},null,2));
      if (!extracted.next || products.length === before) break;
      await page.goto(extracted.next,{waitUntil:'domcontentloaded',timeout:45000});
    }
    if (!products.length) throw Error(`页面未取得可识别商品：${await page.title()}。可能需要登录、页面适配或已触发访问限制。`);
    products = products.slice(0,source.limit || 200);
    if (source.details && source.platform === 'amazon') {
      for (const product of products) {
        progress(`读取商品详情 ${product.product_id}`);
        try {
          await page.goto(product.product_url,{waitUntil:'domcontentloaded',timeout:45000});
          validateSourceScope(page.url(), source, true);
          const detail=await page.evaluate(readAmazonDetail,product.product_id);
          Object.assign(product,Object.fromEntries(Object.entries(detail).filter(([,value]) => value !== null)));
          product.detail_missing=['brand','listed_at','reviews'].filter(key => !detail[key] || Array.isArray(detail[key]) && !detail[key].length);
        } catch(error) {product.detail_error=error.message;}
      }
    }
    return {products, observedDelivery,
      note:`网页商品列表；实际配送地区：${observedDelivery || '未识别'}。${source.details ? '已尝试补充详情和页面可见评论，缺失见逐条记录。' : '未请求详情补充。'} SKU 与精确销量未验证。`,
      marketVerified:false};
  } finally { await context.close(); if(browser) await browser.close(); }
}


const {values:a}=parseArgs({options:{url:{type:'string'},platform:{type:'string'},country:{type:'string'},output:{type:'string'},profile:{type:'string'},browser:{type:'string',default:'chrome'},limit:{type:'string',default:'200'},details:{type:'boolean',default:false},'storage-state':{type:'string'},'python-result':{type:'string'},'expected-origin':{type:'string'},'expected-category':{type:'string'}}});
try {
  for(const k of ['url','platform','country','output','profile']) if(!a[k]) throw Error(`Missing --${k}`);
  if (!Number.isInteger(Number(a.limit)) || Number(a.limit)<1 || Number(a.limit)>200) throw Error('limit 必须在 1–200 之间');
  if (a['python-result'] && a.platform !== 'amazon') throw Error('--python-result 当前仅支持 Amazon');
  const result=await website({id:'source',url:a.url,platform:a.platform,name:a.platform,limit:Number(a.limit),details:a.details,storageState:a['storage-state'],pythonResult:a['python-result'],expectedOrigin:a['expected-origin'],expectedCategory:a['expected-category']},{country:a.country,browser:a.browser},path.resolve(a.profile),message=>console.error(message));
  await mkdir(path.dirname(path.resolve(a.output)),{recursive:true});
  await writeFile(a.output,JSON.stringify(result,null,2));
  console.log(JSON.stringify({count:result.products.length,output:path.resolve(a.output),marketVerified:result.marketVerified}));
} catch(error) {console.error(error.message);process.exitCode=1;}
