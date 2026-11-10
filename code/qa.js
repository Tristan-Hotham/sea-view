// QA: serve the studies folder, open index.html at desktop and phone widths, log console errors and save screenshots to qa/.
// Usage: node code/qa.js [maplibre dist dir]. OpenFreeMap tiles live; Google Fonts and site-nav skipped.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(process.env.PW || 'playwright');
const ROOT = path.resolve(__dirname, '..'), STUDIES = path.dirname(ROOT), SLUG = path.basename(ROOT);
const ML = process.argv[2] || '/tmp/ml/node_modules/maplibre-gl/dist';
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.json': 'application/json', '.png': 'image/png', '.geojson': 'application/json', '.css': 'text/css', '.jpg': 'image/jpeg' };
const PORT = 8800 + Math.floor(Math.random() * 90);
const srv = http.createServer((q, s) => { const f = path.join(STUDIES, decodeURIComponent(q.url.split('?')[0]));
  fs.readFile(f, (e, b) => { if (e) { s.writeHead(404); s.end(); return; } s.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' }); s.end(b); }); }).listen(PORT);
const PAGE = `http://localhost:${PORT}/${SLUG}/index.html`;
const SHOTS = JSON.parse(fs.readFileSync(path.join(__dirname, 'qa_shots.json'), 'utf8'));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const errors = [];
  for (const s of SHOTS) {
    const ctx = await browser.newContext({ viewport: { width: s.w, height: s.h }, deviceScaleFactor: s.dpr || 1 });
    const page = await ctx.newPage();
    await page.route(/cdn\.jsdelivr\.net\/npm\/maplibre-gl@4\.7\.1\/dist\/(.*)/, r => { const f = path.join(ML, r.request().url().split('/dist/')[1]); r.fulfill({ body: fs.readFileSync(f), contentType: f.endsWith('.css') ? 'text/css' : 'application/javascript' }); });
    await page.route(/fonts\.(googleapis|gstatic)\.com|maps\.tristanhotham\.com\/assets/, r => r.abort());
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(`[${s.out}] ${m.text().slice(0, 300)}`); });
    page.on('pageerror', e => errors.push(`[${s.out}] pageerror ${e.message}`));
    await page.goto(`${PAGE}${s.q ? '?' + s.q : ''}`, { waitUntil: 'load' });
    await page.waitForFunction(() => window.__map && window.__map.getLayer('views'), null, { timeout: 120000 });
    await page.evaluate(() => new Promise(res => { const m = window.__map; m.once('idle', () => setTimeout(res, 1500)); setTimeout(res, 40000); }));
    if (s.eval) { await page.evaluate(s.eval); await page.waitForTimeout(3500); }
    const info = await page.evaluate(() => ({ scrollW: document.documentElement.scrollWidth, w: innerWidth, fs: document.querySelectorAll('.mfs-btn').length, pts: window.__map.queryRenderedFeatures({ layers: ['views'] }).length, popup: !!document.querySelector('.maplibregl-popup') }));
    await page.screenshot({ path: path.join(ROOT, s.out), fullPage: !!s.full, timeout: 120000 });
    console.log('ok', s.out, JSON.stringify(info));
    await ctx.close();
  }
  await browser.close(); srv.close();
  console.log('ERRORS:', errors.length); errors.forEach(e => console.log(e));
  process.exit(0);
})();
