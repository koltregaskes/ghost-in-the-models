import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
const root = process.cwd();
const routes = execFileSync('git', ['ls-files', '*.html'], {encoding:'utf8'}).trim().split('\n');
const types = {'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.png':'image/png','.webp':'image/webp','.svg':'image/svg+xml','.woff2':'font/woff2'};
const browser = await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE});
let failures = 0;
try {
  for (const width of [320,1280]) {
    const context = await browser.newContext({viewport:{width,height:900}, reducedMotion:'reduce'});
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
    for (const file of routes) {
      await page.goto(`https://launch.test/${file}`,{waitUntil:'networkidle',timeout:20000});
      const result = await new AxeBuilder({page}).analyze();
      const serious = result.violations.filter(v=>['serious','critical'].includes(v.impact));
      const overflow = await page.evaluate(()=>document.documentElement.scrollWidth > innerWidth);
      if (serious.length || overflow) {
        failures++;
        console.error(JSON.stringify({file,width,overflow,violations:serious.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))}));
      }
    }
    await context.close();
  }
} finally { await browser.close(); }
console.log(`Checked ${routes.length} routes at 320px and 1280px; ${failures} failures`);
if (failures) process.exitCode=1;