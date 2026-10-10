// Executed inside the page; keep dependencies within this function.
export function readAmazonDetail(productId) {
  const text = node => node?.textContent?.trim() || null;
  const title = text(document.querySelector('#productTitle'));
  if (!title) {
    if (document.querySelector('form[action*="validateCaptcha"]')) throw Error('Amazon 返回继续购物验证页面，未取得商品详情；需在浏览器完成验证后更新会话');
    throw Error('未取得商品详情标题，可能是登录或访问限制页面');
  }
  const asin = document.querySelector('input#ASIN')?.value;
  if (asin && asin !== productId) throw Error('详情页商品 ID 与榜单商品不一致');
  const attributes = {};
  document.querySelectorAll('#productOverview_feature_div tr, #productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr, #productDetails_expanderTables_depthLeftSections tr').forEach(row => {
    const cells = [...row.children].filter(n => ['TD','TH'].includes(n.tagName));
    if (cells.length === 2) attributes[text(cells[0])?.replace(/[:\s\u200e\u200f]+$/g,'')] = text(cells[1]);
  });
  document.querySelectorAll('#detailBullets_feature_div li').forEach(row => {
    const label = text(row.querySelector('.a-text-bold'));
    if (label) attributes[label.replace(/[:\s\u200e\u200f]+$/g,'')] = text(row).replace(label,'').replace(/^[:\s\u200e\u200f]+/g,'');
  });
  const reviews=[], seen=new Set();
  document.querySelectorAll('[data-hook="review"]').forEach(row => {
    const body=text(row.querySelector('[data-hook="reviewRichContentContainer"], [data-hook="review-body"]'));
    if (!row.id || !body || seen.has(row.id)) return;
    seen.add(row.id);
    const rating=text(row.querySelector('[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]'))?.match(/\d+[.,]?\d*/)?.[0];
    reviews.push({id:row.id,text:body,rating:rating ? Number(rating.replace(',','.')) : null,
      date:text(row.querySelector('[data-hook="review-date"]')),variation:text(row.querySelector('[data-hook="format-strip"]')),
      url:new URL('/gp/customer-reviews/'+row.id,location.href).href,sampling:'商品详情页可见评论；可能包含多个变体'});
  });
  const count=text(document.querySelector('#acrCustomerReviewText'))?.replace(/\D/g,'');
  const bylineBrand=text(document.querySelector('#bylineInfo'))?.match(/^Brand:\s*(.+)/)?.[1];
  const ratingNode=document.querySelector('#acrPopover');
  const ratingRaw=ratingNode?.getAttribute('title') || text(ratingNode) || '';
  const ratingValue=ratingRaw.match(/\d+[.,]?\d*/)?.[0];
  const image=document.querySelector('#landingImage, #imgBlkFront');
  const imageAsin=image && asin===productId ? asin : null;
  const gallery=[];
  if (imageAsin) {
    for (const script of document.querySelectorAll('script')) {
      const match=script.textContent.match(/'colorImages'\s*:\s*\{\s*'initial'\s*:\s*A\.\$\.parseJSON\('((?:\\.|[^'\\])*)'\)/);
      if (!match) continue;
      let images;
      try { images=JSON.parse(match[1].replace(/\\'/g,"'")); } catch { continue; }
      const main=images.find(item=>item.variant==='MAIN');
      const displayedAsset=(image.getAttribute('data-old-hires') || image.src || '').match(/\/images\/I\/([^/.]+)/)?.[1];
      const galleryAsset=(main?.hiRes || main?.large || '').match(/\/images\/I\/([^/.]+)/)?.[1];
      if (!displayedAsset || displayedAsset!==galleryAsset) continue;
      const urls=new Set();
      for (const item of images) {
        const url=item.hiRes || item.large;
        if (url && /^https?:\/\//.test(url) && !urls.has(url)) {
          urls.add(url);gallery.push({url,image_role:item.variant ?? null,asin:imageAsin,scope:'selected_asin',source:location.href});
        }
      }
      if (gallery.length) break;
    }
  }
  const feature_bullets=[...new Set([...document.querySelectorAll('#feature-bullets li .a-list-item')].map(text).filter(Boolean))];
  const priceRoot=document.querySelector('#corePriceDisplay_desktop_feature_div, #corePrice_feature_div');
  function amount(node) {
    if (!node) return null;
    const whole=node.querySelector('.a-price-whole'), fraction=node.querySelector('.a-price-fraction');
    if (whole) {
      const digits=whole.textContent.replace(/\D/g,'');
      if (digits) return Number(digits+'.'+(fraction ? fraction.textContent.replace(/\D/g,'') : '0'));
    }
    const match=node.querySelector('.a-offscreen')?.textContent.match(/([\d,]+\.\d{2})/);
    return match ? Number(match[1].replace(/,/g,'')) : null;
  }
  const currentNode=priceRoot?.querySelector('.priceToPay, .apex-pricetopay-value');
  const referenceNode=priceRoot?.querySelector('.basisPrice .a-text-price');
  const currentPrice=amount(currentNode), referencePrice=amount(referenceNode);
  const symbol=text(currentNode?.querySelector('.a-price-symbol'));
  const currency=({'€':'EUR','£':'GBP'})[symbol] || (symbol==='$' && ['amazon.com','www.amazon.com'].includes(location.hostname) ? 'USD' : null);
  const pricing={current_price:currentPrice,reference_price:referencePrice,currency,currency_symbol:symbol,
    reference_label:text(priceRoot?.querySelector('.basisPrice')),source:location.href,
    discount_percent:currentPrice!==null && referencePrice>currentPrice ? Math.round((1-currentPrice/referencePrice)*10000)/100 : null};
  return {title,brand:attributes.Brand || attributes['Brand Name'] || attributes['品牌'] || bylineBrand || null,listed_at:attributes['Date First Available'] || attributes['上架时间'] || null,
    rating:ratingValue ? Number(ratingValue.replace(',','.')) : null,rating_raw:ratingRaw,
    listed_at_kind:'source_display',attributes,rating_count:count ? Number(count) : null,review_count:null,
    image_url:image?.getAttribute('data-old-hires') || image?.src || null,image_scope:imageAsin ? 'selected_asin' : 'product',image_asin:imageAsin,
    displayed_sales_message:text(document.querySelector('#social-proofing-faceout-title-tk_bought')),
    pricing,gallery,gallery_status:gallery.length ? 'embedded_initial' : 'not_observed',
    feature_bullets,reviews,detail_source:location.href};
}
