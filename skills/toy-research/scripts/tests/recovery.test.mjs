import test from 'node:test';
import assert from 'node:assert/strict';
import { recoverAmazon } from '../amazon_recovery.mjs';

const source = {url:'https://www.amazon.com/zgbs/toys-and-games', details:true};
function fixture() {
  return {source_url:source.url, platform:'amazon', country:'US', note:'Python',
    products:[{product_id:'B000000001',title:'Existing',rank:1}],
    unresolved_products:[2,3].map(n => ({product_id:`B00000000${n}`,rank:n,
      product_url:`https://www.amazon.com/dp/B00000000${n}`,error:'HTTP failure'})),
    coverage:{target:100,actual:1,missing:99,missing_declared_ranks:[2,3],source_range_shortfall:true},
    pagination_error:'previous page error'};
}
function fakePage(read) {
  const visited = [];
  return {visited, goto:async url => {visited.push(url);},url:() => visited.at(-1),
    locator:() => ({innerText:async () => 'Deliver to New York 10001'}),
    evaluate:async (_,asin) => read(asin)};
}
test('recover only known ASINs, retain original ranks and Python evidence', async () => {
  const input = fixture();
  const page = fakePage(asin => ({title:`Toy ${asin}`,image_asin:asin}));
  const result = await recoverAmazon(page,input,source,'US',()=>{});
  assert.equal(page.visited.length,2);
  assert.deepEqual(result.products.map(p=>p.rank),[1,2,3]);
  assert.equal(result.products[1].image_asin,'B000000002');
  assert.equal(result.coverage.actual,3);
  assert.equal(result.coverage.missing,97);
  assert.equal(result.coverage.source_range_shortfall,true);
  assert.equal(result.pagination_error,input.pagination_error);
  assert.deepEqual(result.coverage.missing_declared_ranks,[]);
  assert.equal(result.recovery_attempts[0].python_error,'HTTP failure');
  assert.equal(input.products.length,1);
});
test('ASIN mismatch remains unresolved; challenge stops subsequent requests', async () => {
  const input = fixture();
  input.unresolved_products.push({product_id:'B000000004',rank:4});
  const page = fakePage(asin => {
    throw Error(asin === 'B000000002' ? '详情页商品 ID 与榜单商品不一致' : 'Amazon 返回继续购物验证页面');
  });
  const result = await recoverAmazon(page,input,source,'US',()=>{});
  assert.equal(page.visited.length,2);
  assert.equal(result.products.length,1);
  assert.equal(result.unresolved_products.length,3);
  assert.match(result.recovery_stopped,/验证页面/);
});
test('different market cannot be relabeled or requested', async () => {
  const page = fakePage(()=>assert.fail());
  await assert.rejects(recoverAmazon(page,fixture(),source,'CA',()=>{}),/国家/);
  assert.equal(page.visited.length,0);
});
test('source range shortfall alone makes no request', async () => {
  const input=fixture();
  input.unresolved_products=[];
  const page=fakePage(()=>assert.fail());
  const result=await recoverAmazon(page,input,source,'US',()=>{});
  assert.equal(page.visited.length,0);
  assert.equal(result.coverage.actual,1);
});
test('deferred details can resume and retain their original reason', async () => {
  const input=fixture();
  input.unresolved_products=[];
  input.products[0].product_url='https://www.amazon.com/dp/B000000001';
  input.products[0].detail_deferred_reason='Earlier request returned a challenge';
  const page=fakePage(()=>({title:'Recovered toy',brand:'Observed brand'}));
  const result=await recoverAmazon(page,input,source,'US',()=>{});
  assert.equal(page.visited.length,1);
  assert.equal(result.products[0].brand,'Observed brand');
  assert.equal(result.products[0].detail_deferred_reason,undefined);
  assert.equal(result.recovery_attempts[0].python_deferred_reason,input.products[0].detail_deferred_reason);
});
