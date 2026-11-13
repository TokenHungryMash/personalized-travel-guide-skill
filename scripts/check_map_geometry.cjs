/* Browser regression for non-default offline map dimensions and aspect ratios. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { browserRuntime } = require('./browser_runtime.cjs');

const root = path.resolve(process.argv[2] || '.');
const { chromium, executablePath } = browserRuntime(root);
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'journal-map-geometry-'));

async function main() {
  const original = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const dataPattern = /(<script id="guide-data" type="application\/json">)([\s\S]*?)(<\/script>)/;
  const match = original.match(dataPattern);
  assert(match, 'Build index.html before running the map geometry check');
  for (const file of fs.readdirSync(root)) {
    if (['.js', '.css'].includes(path.extname(file))) {
      fs.copyFileSync(path.join(root, file), path.join(temporary, file));
    }
  }
  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    page.setDefaultTimeout(10000);
    for (const [width, height] of [[1400, 1100], [1000, 500], [600, 1000]]) {
      const guide = JSON.parse(match[2]);
      const ids = guide.days[0].stops.slice(0, 2).map(stop => stop[1]);
      assert.equal(ids.length, 2, 'Geometry check requires a day with two stops');
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="100%" height="100%" fill="#e0e9dc"/></svg>`;
      const src = 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');
      const pins = ids.map((id, index) => {
        const fraction = 0.25 + index * 0.03;
        return { id, number: index + 1, px: fraction * width, py: fraction * height, x: fraction * 100, y: fraction * 100 };
      });
      for (const key of Object.keys(guide.maps)) {
        guide.maps[key] = { src, title: 'Geometry fixture', ids, mappedIds: ids, pins,
          projection: { width, height }, note: 'Test fixture', attribution: 'Test fixture' };
      }
      guide.edition.overviewIds = ids;
      const html = original.replace(dataPattern, (_, before, _data, after) => before + JSON.stringify(guide).replaceAll('</', '<\\/') + after);
      const file = path.join(temporary, 'fixture.html');
      fs.writeFileSync(file, html);
      await page.goto(pathToFileURL(file).href);
      await page.waitForSelector('.journey-map-sheet svg');
      for (const viewport of [1440, 390]) {
        await page.setViewportSize({ width: viewport, height: 900 });
        await page.locator('#journey-overview').scrollIntoViewIfNeeded();
        const geometry = await page.evaluate(() => {
          const svg = document.querySelector('.journey-map-sheet svg');
          const image = document.querySelector('.journey-map-sheet img').getBoundingClientRect();
          const circle = svg.querySelector('[data-map-dot] circle');
          const point = new DOMPoint(Number(circle.getAttribute('cx')), Number(circle.getAttribute('cy'))).matrixTransform(svg.getScreenCTM());
          return { viewBox: svg.getAttribute('viewBox'), x: (point.x - image.left) / image.width,
            y: (point.y - image.top) / image.height, ratio: image.width / image.height };
        });
        assert.equal(geometry.viewBox, `0 0 ${width} ${height}`);
        assert(Math.abs(geometry.x - 0.25) < 0.002, JSON.stringify(geometry));
        assert(Math.abs(geometry.y - 0.25) < 0.002, JSON.stringify(geometry));
        assert(Math.abs(geometry.ratio - width / height) < 0.002);
        await page.locator('#itinerary').scrollIntoViewIfNeeded();
        await page.locator('#day-view .route-fold').evaluate(fold => { fold.open = true; });
        const atlas = await page.locator('#day-view .atlas-art').first().evaluate(art => {
          const image = art.querySelector('img').getBoundingClientRect();
          const svg = art.querySelector('svg');
          const circle = svg.querySelector('circle');
          const point = new DOMPoint(Number(circle.getAttribute('cx')), Number(circle.getAttribute('cy'))).matrixTransform(svg.getScreenCTM());
          return { viewBox: svg.getAttribute('viewBox'), x: (point.x - image.left) / image.width,
            y: (point.y - image.top) / image.height, ratio: image.width / image.height };
        });
        assert.equal(atlas.viewBox, `0 0 ${width} ${height}`);
        assert(Math.abs(atlas.x - 0.25) < 0.002, JSON.stringify(atlas));
        assert(Math.abs(atlas.y - 0.25) < 0.002, JSON.stringify(atlas));
        assert(Math.abs(atlas.ratio - width / height) < 0.002);
        await page.locator('#day-view [data-map-open]').first().click();
        const fit = await page.locator('#map-large-wrap').evaluate(stage => {
          const pane = stage.closest('.map-pan');
          return { width: stage.getBoundingClientRect().width, height: stage.getBoundingClientRect().height,
            paneWidth: pane.clientWidth, paneHeight: pane.clientHeight };
        });
        assert(fit.width <= fit.paneWidth + 1 && fit.height <= fit.paneHeight + 1, JSON.stringify(fit));
        assert(Math.abs(fit.width / fit.height - width / height) < 0.002);
        await page.locator('#map-dialog [data-map-close]').click();
      }
    }
    console.log('PASS map geometry: 1400x1100, 1000x500, 600x1000; desktop/mobile overview, leader anchors and fit zoom');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => {
  fs.rmSync(temporary, { recursive: true, force: true });
});
