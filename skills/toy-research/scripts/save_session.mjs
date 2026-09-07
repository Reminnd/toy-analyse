import {chromium} from 'playwright';
import {parseArgs} from 'node:util';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {createInterface} from 'node:readline/promises';

const {values:a}=parseArgs({options:{url:{type:'string'},output:{type:'string'},browser:{type:'string',default:'chrome'}}});
if (!a.url || !a.output) throw Error('Required: --url --output');
if (!process.stdin.isTTY) throw Error('请在交互终端运行，由用户完成登录后按 Enter 保存');
const browser=await chromium.launch({channel:a.browser==='chromium'?undefined:a.browser,headless:false});
const context=await browser.newContext();
const input=createInterface({input:process.stdin,output:process.stdout});
try {
  const page=await context.newPage();
  await page.goto(a.url,{waitUntil:'domcontentloaded'});
  await input.question('请在浏览器完成登录并确认目标站点/配送地区，返回此终端按 Enter 保存状态：');
  const state=await context.storageState({indexedDB:true});
  state.user_agent=await page.evaluate(()=>navigator.userAgent);
  await mkdir(path.dirname(path.resolve(a.output)),{recursive:true});
  await writeFile(a.output,JSON.stringify(state,null,2),{mode:0o600});
  console.log('登录状态已保存。文件包含会话凭证，不要分享或放入报告包。');
} finally {input.close();await browser.close();}
