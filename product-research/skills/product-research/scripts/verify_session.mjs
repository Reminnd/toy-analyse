import {chromium} from 'playwright';
import {parseArgs} from 'node:util';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export async function waitForAmazonPage(page, origin) {
  await page.waitForFunction(expected => {
    if (location.origin !== expected) return false;
    if (document.querySelector('form[action*="validateCaptcha"], #captchacharacters, #authportal-main-section')) return false;
    const text = document.body?.innerText || '';
    if (/click the button below to continue shopping|enter the characters you see below/i.test(text)) return false;
    return !!document.querySelector('#productTitle, [id="gridItemRoot"] a[href*="/dp/"], .zg-item-immersion a[href*="/dp/"]');
  }, origin, {timeout:0, polling:1000});
}

export async function verifySession({url, output, storageState}) {
  const state = storageState ? JSON.parse(await readFile(storageState, 'utf8')) : null;
  const browser = await chromium.launch({channel:'chrome', headless:false});
  try {
    const context = await browser.newContext(state ? {
      storageState:{cookies:state.cookies, origins:state.origins}, userAgent:state.user_agent,
    } : {});
    const page = await context.newPage();
    console.error('请在打开的 Amazon 浏览器中手动完成验证；正常页面出现后会自动保存会话并继续。关闭浏览器则停止续采。');
    await page.goto(url, {waitUntil:'domcontentloaded', timeout:45000});
    await waitForAmazonPage(page, new URL(url).origin);
    const saved = await context.storageState({indexedDB:true});
    saved.user_agent = await page.evaluate(() => navigator.userAgent);
    await mkdir(path.dirname(path.resolve(output)), {recursive:true});
    await writeFile(output, JSON.stringify(saved, null, 2), {mode:0o600});
    return {saved:true};
  } finally {
    await browser.close();
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const {values:a} = parseArgs({options:{url:{type:'string'}, output:{type:'string'}, 'storage-state':{type:'string'}}});
  try {
    console.log(JSON.stringify(await verifySession({url:a.url, output:a.output, storageState:a['storage-state']})));
  } catch (error) {
    console.error('验证未完成，原有数据与会话保留：' + error.message);
    process.exitCode = 2;
  }
}
