/* Exercise real directory rendering with large fixture lists in temporary HTML files. */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { browserRuntime } = require('./browser_runtime.cjs');

const root = path.resolve(process.argv[2] || '.');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'build-manifest.json'), 'utf8'));
const original = fs.readFileSync(path.join(root, manifest.artifact), 'utf8');
const cssPath = path.resolve(process.argv[3] || path.join(__dirname, '../assets/destination-reference/reader-components.css'));
const css = fs.readFileSync(cssPath, 'utf8');
const dataPattern = /(<script id="guide-data" type="application\/json">)([\s\S]*?)(<\/script>)/;
const sourceGuide = JSON.parse(original.match(dataPattern)[2]);
const readerStyle = /<style>[^<]*--reader-caption:[\s\S]*?<\/style>/;
assert(readerStyle.test(original), 'Fixture HTML must contain the embedded reader-components stylesheet');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'journal-pagination-'));

function fixture(count) {
  const guide = structuredClone(sourceGuide);
  const originals = guide.places;
  guide.places = Array.from({ length: count }, (_, index) => index < originals.length
    ? originals[index]
    : { ...originals[index % originals.length], id: `pagination-fixture-${index}`, name: `分页验证地点 ${index + 1}` });
  const html = original.replace(readerStyle, () => `<style>${css}</style>`)
    .replace(dataPattern, (_, start, text, end) => start + JSON.stringify(guide).replaceAll('</', '<\\/') + end);
  const file = path.join(temporary, `directory-${count}.html`);
  fs.writeFileSync(file, html);
  return file;
}

async function checkBounds(page) {
  const bounds = await page.locator('#directory-pages button').evaluateAll(buttons => buttons.map(button => {
    const rect = button.getBoundingClientRect();
    return { text: button.textContent, left: rect.left, right: rect.right, width: rect.width, height: rect.height };
  }));
  const viewport = page.viewportSize().width;
  assert(bounds.every(rect => rect.left >= -1 && rect.right <= viewport + 1), JSON.stringify(bounds));
  assert(bounds.every(rect => rect.width >= 43 && rect.height >= 43), 'Pagination controls must remain tappable');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Directory causes horizontal overflow');
}

(async () => {
  const { chromium, executablePath } = browserRuntime(root);
  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    for (const count of [60, 100]) {
      const file = fixture(count);
      for (const width of [320, 390, 1440]) {
        const page = await browser.newPage({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.route(/^https?:/, route => route.abort());
        await page.goto(pathToFileURL(file).href);
        await page.evaluate(() => document.fonts.ready);
        const pages = Math.ceil(count / 6);
        const pagination = page.locator('#directory-pages');
        await pagination.scrollIntoViewIfNeeded();
        assert.equal(await pagination.locator('div button').count(), pages);
        await checkBounds(page);
        await pagination.locator(`div [data-directory-page="${pages}"]`).click();
        assert.equal(await pagination.locator('[aria-current=page]').textContent(), String(pages));
        assert.equal(await page.locator('#place-results [data-directory-id]').count(), count - (pages - 1) * 6);
        assert.equal(await page.evaluate(() => document.activeElement.id), 'result-count');
        await pagination.locator('button').filter({ hasText: '上一页' }).click();
        assert.equal(await pagination.locator('[aria-current=page]').textContent(), String(pages - 1));
        await pagination.locator('div [data-directory-page="1"]').click();
        await pagination.locator('button').filter({ hasText: '下一页' }).click();
        assert.equal(await pagination.locator('[aria-current=page]').textContent(), '2');
        await page.locator('#place-search').fill('没有此地点-分页测试');
        assert.equal(await pagination.locator('button').count(), 0);
        await page.locator('#place-search').fill('');
        assert.equal(await pagination.locator('[aria-current=page]').textContent(), '1');
        await pagination.scrollIntoViewIfNeeded();
        await checkBounds(page);
        await page.screenshot({ path: path.join(temporary, `directory-${count}-${width}.png`) });
        assert.deepEqual(errors, []);
        await page.close();
      }
    }
    console.log('PASS directory pagination: 60/100 places at 320/390/1440, bounds, touch targets, last/previous/next, search reset and keyboard focus.');
    console.log('Screenshots: ' + temporary);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
