import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { findOverflow } from './check-overflow.mjs';
const root = process.cwd();
const watchdog = setTimeout(() => {
  console.error('Audit exceeded 250 seconds; stopping this audit and its browser.');
  if (process.platform === 'win32') execFileSync('taskkill', ['/PID',String(process.pid),'/T','/F']);
  process.exit(124);
},250000);
watchdog.unref();
console.log('Edge audit PID '+process.pid);
const allRoutes = execFileSync('git', ['ls-files', '*.html'], {encoding:'utf8'}).trim().split('\n');
const [shard,parts]=(process.env.ROUTE_SHARD || '1/1').split('/').map(Number);
if (!Number.isInteger(shard)||!Number.isInteger(parts)||shard<1||parts<1||shard>parts) throw new Error('Invalid ROUTE_SHARD.');
const routes=allRoutes.filter((_,index)=>index%parts===shard-1);
const width = Number(process.env.VIEWPORT_WIDTH || 320);
if (![320,390,1280].includes(width)) throw new Error('VIEWPORT_WIDTH must be 320, 390 or 1280.');
const types = {'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.png':'image/png','.webp':'image/webp','.svg':'image/svg+xml','.woff2':'font/woff2'};
// The test owns this fresh headless browser and always closes it. No downloads/server/profile.
const browser = await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL || 'msedge',timeout:15000});
let failures = 0;
const deadline = Date.now()+250000;
try {
  const context = await browser.newContext({viewport:{width,height:900}, reducedMotion:'reduce'});
  context.setDefaultTimeout(10000);
  await context.route('https://launch.test/**', async route => {
    const url = new URL(route.request().url());
    let file = decodeURIComponent(url.pathname).replace(/^\/+/, '');
    if (!file || file.endsWith('/')) file += 'index.html';
    const target = path.resolve(root,file);
    if (!target.startsWith(root + path.sep)) return route.fulfill({status:403,body:''});
    try { await route.fulfill({status:200,contentType:types[path.extname(file)] || 'application/octet-stream',body:await readFile(target)}); }
    catch { await route.fulfill({status:404,body:'Missing asset'}); }
  });
  const page = await context.newPage();
  if (width<700) {
    await page.goto('https://launch.test/about.html',{waitUntil:'load',timeout:15000});
    await page.evaluate(()=>{ const probe=document.createElement('canvas'); probe.id='overflow-negative-probe'; probe.style.width='2000px'; document.querySelector('main').append(probe); });
    if (!(await page.evaluate(findOverflow)).some(item=>item.id==='overflow-negative-probe')) throw new Error('Negative test failed: clipped wide element was missed at '+width);
    console.log('Negative overflow test detected planted wide canvas at '+width+'px.');
    await page.goto('https://launch.test/posts/2026-01-03-project-aegis.html',{waitUntil:'load',timeout:15000});
    await page.evaluate(()=>{
      const main=document.querySelector('main.gitm-reader'); main.style.overflowX='clip';
      const pre=document.createElement('pre'); pre.id='text-overflow-negative-probe';
      pre.style.cssText='box-sizing:border-box;width:100%;max-width:100%;white-space:pre;overflow:visible;overflow-wrap:normal;word-break:normal';
      pre.textContent='unbroken'.repeat(50); main.append(pre);
    });
    if (!(await page.evaluate(findOverflow)).some(item=>item.id==='text-overflow-negative-probe'&&item.textOverflow)) throw new Error('Negative test failed: clipped pre text was missed at '+width);
    await page.evaluate(()=>{
      const pre=document.getElementById('text-overflow-negative-probe'); pre.style.overflowX='auto';pre.tabIndex=0;pre.setAttribute('role','region');pre.setAttribute('aria-label','Scrollable code example');
    });
    if ((await page.evaluate(findOverflow)).some(item=>item.id==='text-overflow-negative-probe')) throw new Error('Labelled focusable code scroller was rejected at '+width);
    await page.evaluate(()=>document.getElementById('text-overflow-negative-probe').removeAttribute('aria-label'));
    if (!(await page.evaluate(findOverflow)).some(item=>item.id==='text-overflow-negative-probe'&&item.textOverflow)) throw new Error('Unlabelled code scroller was missed at '+width);
    console.log('Clipped pre text detected; labelled focusable scroller allowed; unlabelled scroller rejected at '+width+'px.');
  }
  // Check both original box guards at every audited width, independently of text exemptions.
  await page.goto('https://launch.test/posts/2026-01-03-project-aegis.html',{waitUntil:'load',timeout:15000});
  if ((await page.evaluate(findOverflow)).length) throw new Error('Aegis baseline/table should remain accessible at '+width);
  await page.evaluate(()=>{
    const probe=document.createElement('div');probe.id='wide-intentional-probe';probe.className='gitm-lifewire__viewport';probe.style.cssText='width:3000px;height:20px;flex:none';document.querySelector('main').append(probe);
  });
  if (!(await page.evaluate(findOverflow)).some(item=>item.id==='wide-intentional-probe')) throw new Error('Oversized intentional element escaped box guard at '+width);
  await page.evaluate(()=>{
    document.getElementById('wide-intentional-probe').remove();
    const clip=document.createElement('div');clip.id='narrow-clip-probe';clip.style.cssText='width:150px;height:40px;overflow:hidden';
    const scroller=document.createElement('div');scroller.id='clipped-scroller-probe';scroller.style.cssText='width:280px;height:30px;overflow-x:auto';scroller.tabIndex=0;scroller.setAttribute('role','region');scroller.setAttribute('aria-label','Clipped scroller control');scroller.textContent='A labelled scroller';clip.append(scroller);document.querySelector('main').append(clip);
  });
  if (!(await page.evaluate(findOverflow)).some(item=>item.id==='clipped-scroller-probe'&&item.clipped)) throw new Error('Ancestor-clipped labelled scroller escaped box guard at '+width);
  await page.evaluate(()=>document.getElementById('narrow-clip-probe').remove());
  if ((await page.evaluate(findOverflow)).length) throw new Error('Aegis baseline changed after negative probes at '+width);
  console.log('Oversized intentional element and clipped labelled scroller detected; Aegis table allowed at '+width+'px.');
  for (const file of routes) {
    console.log('Checking '+width+'px '+file);
    if (Date.now()>deadline) throw new Error('Stopped before five-minute command limit.');
    await page.goto(`https://launch.test/${file}`,{waitUntil:'load',timeout:15000});
    await page.waitForFunction(()=>document.fonts.status==='loaded',null,{timeout:15000});
    const result = await new AxeBuilder({page}).analyze();
    // All severities: includes landmarks, heading order, names, labels, alt and contrast.
    const violations = result.violations;
    const keyboard = await page.evaluate(() => {
      const selector='a[href],button,input,select,textarea,summary,[tabindex]';
      const elements=[...document.querySelectorAll(selector)];
      elements.forEach((element,index)=>element.setAttribute('data-a11y-probe',String(index)));
      return {max:elements.length*2+8};
    });
    const reached=new Set(); const keyboardErrors=[];
    for (let step=0;step<keyboard.max;step++) {
      await page.keyboard.press('Tab');
      const focus=await page.evaluate(()=>{
        const element=document.activeElement;
        if (!element || element===document.body) return null;
        const style=getComputedStyle(element); const rect=element.getBoundingClientRect();
        return {id:element.getAttribute('data-a11y-probe'),tag:element.tagName,
          visible:rect.width>0 && rect.height>0 && style.visibility!=='hidden' && style.display!=='none',
          indicator:(style.outlineStyle!=='none' && parseFloat(style.outlineWidth)>0)||style.boxShadow!=='none',
          summary:element.tagName==='SUMMARY' && !element.parentElement.open};
      });
      if (!focus) continue;
      // Native media controls have shadow focus but no document probe id.
      if (focus.id === null) continue;
      if (reached.has(focus.id)) break;
      reached.add(focus.id);
      if (!focus.visible || !focus.indicator) keyboardErrors.push({focus:focus.id,tag:focus.tag,visible:focus.visible,indicator:focus.indicator});
      if (focus.summary) {
        await page.keyboard.press('Enter');
        if (!await page.evaluate(()=>document.activeElement.parentElement.open)) keyboardErrors.push({summary:focus.id,reason:'Enter did not open details'});
      }
    }
    const unreachable=await page.evaluate((ids)=>[...document.querySelectorAll('[data-a11y-probe]')].filter(element=>{
      const rect=element.getBoundingClientRect();
      return element.tabIndex>=0 && !element.disabled && rect.width>0 && rect.height>0 && !ids.includes(element.getAttribute('data-a11y-probe'));
    }).map(element=>element.getAttribute('data-a11y-probe')),[...reached]);
    const overflowElements = await page.evaluate(findOverflow);
    const overflow = overflowElements.length>0;
    if (violations.length || overflow || keyboardErrors.length || unreachable.length) {
      failures++;
      console.error(JSON.stringify({file,width,overflow,overflowElements,keyboardErrors,unreachable,violations:violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}));
    }
  }
  await context.close();
} finally { await browser.close(); }
console.log(`Checked ${routes.length}/${allRoutes.length} routes (shard ${shard}/${parts}) at ${width}px with installed ${process.env.PLAYWRIGHT_CHANNEL || 'msedge'}: all-severity axe, Tab/Enter reachability and visible focus; ${failures} failures.`);
if (failures) process.exitCode=1;