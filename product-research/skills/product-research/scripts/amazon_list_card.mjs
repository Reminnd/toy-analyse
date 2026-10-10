// Executed in the browser; only accept the original ASIN and observed rank.
export function readAmazonListCard({asin, rank}) {
  if (document.querySelector('form[action*="validateCaptcha"]')) throw Error('Amazon 返回验证页面');
  for (const card of document.querySelectorAll('[id="gridItemRoot"], .zg-item-immersion')) {
    const links = [...card.querySelectorAll('a[href*="/dp/"]')]
      .filter(a => a.href.match(/\/dp\/([A-Z0-9]{10})/)?.[1] === asin);
    if (!links.length) continue;
    const observedRank = Number(card.querySelector('.zg-bdg-text')?.textContent.replace(/\D/g,''));
    if (observedRank !== rank) throw Error('原榜单 ASIN 当前排名已变化，不能覆盖旧排名记录');
    const image = card.querySelector('img');
    const link = links.find(a => a.textContent.trim().length > 15) || links[0];
    const title = link.textContent.trim() || image?.alt || '';
    if (!title) return null;
    const ratingRaw = card.querySelector('.a-icon-alt')?.textContent || '';
    const rating = ratingRaw.match(/\d+[.,]?\d*/)?.[0];
    return {title, image_url:image?.src || null, image_scope:'product',
      rating:rating ? Number(rating.replace(',','.')) : null, rating_raw:ratingRaw,
      list_card_source:location.href};
  }
  return null;
}

export async function recoverListCard(page, original, candidate) {
  const urls = [...new Set((original.pages || []).map(p => p.url))];
  if (!urls.length) urls.push(original.source_url);
  for (const url of urls) {
    await page.goto(url, {waitUntil:'domcontentloaded',timeout:45000});
    let stableBottom = 0;
    for (let step=0; step<40 && stableBottom<3; step++) {
      const card = await page.evaluate(readAmazonListCard, {asin:candidate.product_id,rank:candidate.rank});
      if (card) return card;
      await page.evaluate(() => window.scrollBy(0,850));
      await page.waitForTimeout(450);
      const bottom = await page.evaluate(() => window.innerHeight+window.scrollY >= document.documentElement.scrollHeight-5);
      stableBottom = bottom ? stableBottom+1 : 0;
    }
  }
  throw Error('已读原榜单页面中未找到匹配 ASIN 和排名的完整卡片');
}
