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
  document.querySelectorAll('#productOverview_feature_div tr, #productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr').forEach(row => {
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
  return {title,brand:attributes.Brand || attributes['品牌'] || bylineBrand || null,listed_at:attributes['Date First Available'] || attributes['上架时间'] || null,
    rating:ratingValue ? Number(ratingValue.replace(',','.')) : null,rating_raw:ratingRaw,
    listed_at_kind:'source_display',attributes,rating_count:count ? Number(count) : null,review_count:null,
    image_url:image?.getAttribute('data-old-hires') || image?.src || null,image_scope:'product',
    displayed_sales_message:text(document.querySelector('#social-proofing-faceout-title-tk_bought')),
    reviews,detail_source:location.href};
}
