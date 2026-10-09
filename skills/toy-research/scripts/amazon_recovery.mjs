import { readAmazonDetail } from './amazon_detail.mjs';

// Consume declared ASINs only; a source-range shortfall is not a retry queue.
export async function recoverAmazon(page, original, source, country, progress) {
  if (original.platform !== 'amazon' || original.country !== country || original.source_url !== source.url) {
    throw Error('Python 结果缺少匹配的来源 URL、平台或国家；请使用新版 Python 爬虫重新采集');
  }
  const result = structuredClone(original);
  const products = new Map(result.products.map(p => [p.product_id, p]));
  const pending = new Map((result.unresolved_products || []).map(p => [p.product_id, p]));
  if (source.details) {
    for (const p of products.values()) if (p.detail_error || p.detail_deferred_reason) pending.set(p.product_id, p);
  }
  const attempts = [];
  for (const [asin, candidate] of pending) {
    if (!products.has(asin) && products.size >= result.coverage.target) continue;
    progress(`定向补采 ${asin} · 原排名 ${candidate.rank}`);
    const attempt = {product_id:asin, rank:candidate.rank,
      python_error:candidate.error || candidate.detail_error,
      python_deferred_reason:candidate.deferred_reason || candidate.detail_deferred_reason};
    try {
      await page.goto(candidate.product_url, {waitUntil:'domcontentloaded',timeout:45000});
      attempt.url = page.url();
      attempt.observedDelivery = await page.locator('#glow-ingress-block').innerText().catch(() => '');
      const detail = await page.evaluate(readAmazonDetail, asin);
      const product = {...candidate,
        ...Object.fromEntries(Object.entries(detail).filter(([,value]) => value !== null)),
        collected_at:new Date().toISOString(), recovery_engine:'playwright'};
      // Detail parsing rejects a switched ASIN before any merge occurs.
      delete product.error;
      delete product.detail_error;
      delete product.deferred_reason;
      delete product.detail_deferred_reason;
      delete product.needs_detail;
      product.detail_missing = ['brand','reviews'].filter(key => !detail[key] || Array.isArray(detail[key]) && !detail[key].length);
      products.set(asin, product);
      attempt.status = 'recovered';
    } catch (error) {
      attempt.status = 'failed';
      attempt.error = error.message;
    }
    attempts.push(attempt);
    if (attempt.error && /验证页面|登录或访问限制/.test(attempt.error)) {
      result.recovery_stopped = attempt.error;
      break;
    }
  }
  const recovered = new Set(attempts.filter(a => a.status === 'recovered').map(a => a.product_id));
  result.products = [...products.values()].sort((a,b) => (a.rank ?? Infinity)-(b.rank ?? Infinity));
  result.unresolved_products = (result.unresolved_products || []).filter(p => !recovered.has(p.product_id));
  result.recovery_attempts = attempts;
  const observed = new Set(result.products.map(p => p.rank));
  result.coverage = {...result.coverage, actual:result.products.length,
    missing:Math.max(0,result.coverage.target-result.products.length),
    missing_declared_ranks:result.coverage.missing_declared_ranks.filter(rank => !observed.has(rank))};
  result.marketVerified = false;
  result.note += ' Playwright 仅补采已声明 ASIN；配送地区需结合 recovery_attempts 重新核对，分页失败与来源范围缺口保留。';
  return result;
}
