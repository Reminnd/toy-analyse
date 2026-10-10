import {test} from 'node:test';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {waitForAmazonPage} from '../verify_session.mjs';

test('manual verification waits for valid page and stops when browser closes', async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  try {
    const page = await browser.newPage();
    await page.route('https://www.amazon.com/**', route => route.fulfill({body:'<form action="/errors_page/validateCaptcha">Verify</form>'}));
    await page.goto('https://www.amazon.com/dp/B000000001');
    let completed = false;
    const pending = waitForAmazonPage(page, 'https://www.amazon.com').then(() => { completed = true; });
    await page.waitForTimeout(1100);
    assert.equal(completed, false);
    // Simulate the document after the human has completed verification.
    await page.setContent('<span id="productTitle">Observed product</span>');
    await pending;
    assert.equal(completed, true);
    await page.setContent('<form action="/errors_page/validateCaptcha">Verify</form>');
    const closed = assert.rejects(waitForAmazonPage(page, 'https://www.amazon.com'));
    await page.close();
    await closed;
  } finally { await browser.close(); }
});
