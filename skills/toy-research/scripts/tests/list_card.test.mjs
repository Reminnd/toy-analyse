import test from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { readAmazonListCard } from '../amazon_list_card.mjs';
import { recoverAmazon } from '../amazon_recovery.mjs';

test('original list card recovers identity, while changed ranks and challenges fail', async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const page = await browser.newPage();
    const urls = [];
    const html = '<div id="gridItemRoot"><span class="zg-bdg-text">#39</span>' +
      '<a href="https://www.amazon.com/dp/B0FJ31ZCRB">Toniebox 2 Audio Player Disney Bundle</a>' +
      '<img src="https://example.com/toy.jpg"><span class="a-icon-alt">4.7 out of 5 stars</span></div>';
    await page.route('**/*', route => {
      urls.push(route.request().url());
      return route.fulfill({contentType:'text/html',body:html});
    });
    const source = {url:'https://www.amazon.com/zgbs/toys-and-games'};
    const original = {platform:'amazon',country:'US',source_url:source.url,products:[],note:'Python',
      pages:[{url:source.url}],coverage:{target:100,actual:0,missing:100,missing_declared_ranks:[39]},
      unresolved_products:[{product_id:'B0FJ31ZCRB',title:'',rank:39,
        product_url:'https://www.amazon.com/dp/B0FJ31ZCRB',error:'详情页商品 ID 与榜单商品不一致'}]};
    const result = await recoverAmazon(page,original,source,'US',()=>{});
    assert.equal(result.products[0].rank,39);
    assert.equal(result.products[0].rating,4.7);
    assert.equal(result.products[0].image_scope,'product');
    assert.equal(result.products[0].image_asin,undefined);
    assert.equal(result.products[0].detail_source,undefined);
    assert.equal(result.recovery_attempts[0].scope,'list_card');
    assert.equal(result.unresolved_products.length,0);
    assert.ok(urls.every(url=>!url.includes('/dp/')));
    await page.setContent(html.replace('#39','#40'));
    await assert.rejects(page.evaluate(readAmazonListCard,{asin:'B0FJ31ZCRB',rank:39}),/排名已变化/);
    await page.setContent('<form action="/errors_page/validateCaptcha"></form>');
    await assert.rejects(page.evaluate(readAmazonListCard,{asin:'B0FJ31ZCRB',rank:39}),/验证页面/);
  } finally {await browser.close();}
});
