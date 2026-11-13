/* Ensure actionable copy survives the travel drawer and storage failure paths. */
const fs = require('fs'), path = require('path'), assert = require('assert/strict');
const { pathToFileURL } = require('url');
const R = path.resolve(process.argv[2] || '.');
const { chromium, executablePath } = require('./browser_runtime.cjs').browserRuntime(R);
const manifest = JSON.parse(fs.readFileSync(path.join(R, 'build-manifest.json')));
const artifact = path.join(R, manifest.artifact), html = fs.readFileSync(artifact, 'utf8');
assert.equal(require('crypto').createHash('sha256').update(html).digest('hex'), manifest.sha256);
const qa = path.join(R, 'qa-travel-copy'); fs.mkdirSync(qa, { recursive: true });
const report = { result: 'pending', buildId: manifest.buildId, sha256: manifest.sha256, checks: [], errors: [] };
const normalized = value => String(value ?? '').replace(/\s+/g, ' ').trim();
const withGuide = guide => html.replace(/(<script id="guide-data" type="application\/json">)[\s\S]*?(<\/script>)/, (_, a, b) => a + JSON.stringify(guide).replace(/<\//g, '<\\/') + b);

async function checkPhotoCopy(page, day) {
  await page.locator('.photo-plan-heading').waitFor({ state: 'visible' });
  const shots = day.photoPlan || [], cards = page.locator('#reference-content .photo-shot');
  if (shots.length) {
    assert.equal(await cards.count(), shots.length, 'Photo plan count: ' + day.id);
    for (const [index, shot] of shots.entries()) {
      const text = normalized(await cards.nth(index).innerText());
      for (const key of ['title', 'time', 'light', 'composition', 'portrait', 'settings']) {
        assert(normalized(shot[key]) && text.includes(normalized(shot[key])), 'Missing photo copy: ' + day.id + '/' + index + '/' + key);
      }
      assert.equal(await cards.nth(index).locator('[data-place]').getAttribute('data-place'), shot.placeId, 'Photo place link: ' + day.id + '/' + index);
    }
  } else {
    // Pure transfer/explicit no-photo days may have no plan; old books may keep prose.
    const legacy = [...new Set(day.shooting || [day.photo])].filter(Boolean);
    assert.equal(await cards.count(), legacy.length, 'No-plan/legacy photo state: ' + day.id);
    for (const [index, text] of legacy.entries()) assert(normalized(await cards.nth(index).innerText()).includes(normalized(text)), 'Missing legacy photo note: ' + day.id);
  }
}

(async () => {
  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    const p = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce', acceptDownloads: true });
    p.on('pageerror', e => report.errors.push(e.message));
    await p.route(/^https?:/, r => r.abort());
    await p.goto(pathToFileURL(artifact).href);
    const G = await p.locator('#guide-data').evaluate(e => JSON.parse(e.textContent));
    const places = Object.fromEntries(G.places.map(place => [place.id, place]));
    await p.locator('#pocket-open').click();
    for (let day = 0; day < G.days.length; day++) {
      await p.locator('dialog[open] .tool-day-nav [data-day="' + day + '"]').click();
      const data = G.days[day];
      const fold = p.locator('.pocket-alternatives'), choices = data.alternatives || [];
      if (data.guard || choices.length) {
        assert.equal(await fold.count(), 1, 'One combined daily fold');
        assert.equal(await fold.evaluate(e => e.open), false, 'Daily fold starts collapsed');
        assert.equal(await fold.locator('.alternative-option').count(), choices.length);
        if (choices.length) assert((await fold.locator(':scope>summary').innerText()).includes(choices.length + ' 个备选'));
        if (data.guard) assert.equal(await fold.locator('.pocket-day-guard').isVisible(), false);
        await fold.locator(':scope>summary').focus(); await p.keyboard.press('Enter');
        assert.equal(await fold.evaluate(e => e.open), true, 'Keyboard opens combined fold');
        if (data.guard) {
          assert.equal(await p.locator('.pocket-day-guard').count(), 1, 'Reminder is not duplicated outside fold');
          assert.equal(normalized(await fold.locator('.pocket-day-guard p').innerText()), normalized(data.guard));
          if (choices.length) assert(await fold.evaluate(e => !!(e.querySelector('.pocket-day-guard').compareDocumentPosition(e.querySelector('.alternative-options')) & Node.DOCUMENT_POSITION_FOLLOWING)), 'Reminder before alternatives');
        }
        if (day === 2) { await fold.scrollIntoViewIfNeeded(); await p.screenshot({path:path.join(qa,'daily-fold-open-390.png')}); }
        await fold.locator(':scope>summary').click();
        assert.equal(await fold.locator('.alternative-options').isVisible(), false);
        if (day === 2) { await p.locator('#pocket-dialog .travel-body').evaluate(e=>e.scrollTop=0); await p.screenshot({path:path.join(qa,'daily-fold-closed-390.png')}); }
      } else assert.equal(await fold.count(), 0);
      assert.equal(await p.locator('.pocket-stop').count(), data.stops.length, 'Stop count: ' + data.id);
      for (const [i, stop] of data.stops.entries()) {
        const card = p.locator('.pocket-stop').nth(i), place = places[stop[1]];
        const guard = data.schedules.standard[stop[1]].guard;
        const text = normalized(await card.innerText());
        for (const value of [place.desc, place.walk, place.tip, guard].filter(Boolean)) assert(text.includes(normalized(value)), 'Missing stop copy: ' + data.id + '/' + stop[1]);
        if (guard && guard.trim() === place.tip.trim()) assert.equal(await card.locator('.pocket-time-guard').count(), 0, 'Duplicate tip');
      }
      const shopping = p.locator('.pocket-reading').filter({ has: p.locator('summary', { hasText: '今天怎么买' }) });
      await shopping.locator('summary').click();
      const shoppingText = normalized(await shopping.innerText());
      for (const text of data.shopping) assert(shoppingText.includes(normalized(text)));
      if (day === Math.min(2, G.days.length - 1)) await p.screenshot({ path: path.join(qa, 'day-390.png') });
      await p.locator('dialog[open] .tool-section-nav [data-tool="photos"]').click();
      await p.locator('#reference-upload').waitFor({ state: 'visible' });
      await checkPhotoCopy(p, data);
      await p.locator('dialog[open] .tool-section-nav [data-open-pocket]').click();
    }
    const emptyState = await p.evaluate(() => {
      const host = document.createElement('div'), context = {P:{},esc:text=>text,map:()=>''};
      host.innerHTML = TravelAlternatives.render({guard:'仅有当天提醒',alternatives:[]},context);
      return {reminder:host.querySelector('.pocket-day-guard p')?.textContent,folds:host.querySelectorAll('.pocket-alternatives').length,emptyList:!!host.querySelector('.alternative-options'),empty:TravelAlternatives.render({guard:'',alternatives:[]},context)};
    });
    assert.deepEqual(emptyState,{reminder:'仅有当天提醒',folds:1,emptyList:false,empty:''});
    report.checks.push('All days: one initially collapsed reminder/alternatives fold, keyboard toggle, current-day content, reminder before choices; reminder-only and empty days; stop descriptions/walk/tips/time guards, purchase advice and photo states rendered');
    await p.locator('dialog[open] [data-close]').click();

    // A saved URL is a link, not a PDF. Keep test data isolated in this browser context.
    const storageKey = 'travel-magazine-v4-' + G.edition.slug;
    await p.evaluate(async ({ key, day }) => {
      const request = indexedDB.open(key + '-files', 1);
      const db = await new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error); });
      await new Promise((resolve, reject) => {
        const transaction = db.transaction('files', 'readwrite');
        transaction.objectStore('files').put({ id: 'qa-url', name: '预约网页', type: 'text/plain', day, blob: new Blob(['https://example.com/reservation'], { type: 'text/plain' }) });
        transaction.oncomplete = resolve; transaction.onerror = () => reject(transaction.error);
      }); db.close();
    }, { key: storageKey, day: G.days[0].id });
    await p.locator('#travel-tools [data-tool="files"]').click();
    await p.waitForFunction(() => [...document.querySelectorAll('.file-row')].some(e => e.textContent.includes('预约网页')));
    const row = p.locator('.file-row').filter({ hasText: '预约网页' });
    assert.equal(await row.locator(':scope>span').innerText(), '链接');
    await p.locator('dialog[open] [data-close]').click();
    const existingState = await p.evaluate(key => JSON.parse(localStorage.getItem(key)), storageKey);
    const partial = { format: G.edition.backupFormat || G.edition.slug + '-backup', version: 1, state: existingState, files: [], attachmentsComplete: false };
    await p.locator('#import-data').setInputFiles({ name: 'incomplete-backup.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(partial)) });
    await p.waitForFunction(() => document.querySelector('#toast')?.textContent.includes('附件不完整'));
    await p.locator('#travel-tools [data-tool="files"]').click();
    await p.waitForFunction(() => [...document.querySelectorAll('.file-row')].some(e => e.textContent.includes('预约网页')));
    report.checks.push('Importing a partial backup preserves existing local attachments');
    await p.close();

    // Block attachment reads, not the editorial content or text-state backup.
    const broken = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce', acceptDownloads: true });
    broken.on('pageerror', e => report.errors.push(e.message));
    await broken.route(/^https?:/, r => r.abort());
    await broken.addInitScript(() => { IDBObjectStore.prototype.getAll = function () { throw new DOMException('QA: blocked attachment reads', 'InvalidStateError'); }; });
    await broken.goto(pathToFileURL(artifact).href);
    await broken.locator('#pocket-open').click();
    const photoDay = Math.max(0, G.days.findIndex(d => d.photoPlan?.length));
    await broken.locator('dialog[open] .tool-day-nav [data-day="' + photoDay + '"]').click();
    await broken.locator('dialog[open] .tool-section-nav [data-tool="photos"]').click();
    await broken.waitForFunction(() => document.querySelector('#reference-content')?.textContent.includes('上方拍摄建议仍可使用'));
    assert.equal(await broken.locator('.photo-plan-heading').count(), 1);
    await checkPhotoCopy(broken, G.days[photoDay]);
    await broken.locator('dialog[open] [data-close]').click();
    const downloadEvent = broken.waitForEvent('download'); await broken.locator('#export-data').click();
    const download = await downloadEvent;
    assert(download.suggestedFilename().includes('附件不完整'));
    const backup = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
    assert.equal(backup.attachmentsComplete, false); assert(backup.state); assert.deepEqual(backup.files, []);
    assert(backup.backupNote.includes('未能读取'));
    report.checks.push('Saved URL label; blocked attachment reads keep editorial photo plans; incomplete backup is explicitly labelled');
    await broken.close();

    // Rendering fixtures only: no source data or published itinerary is changed.
    for (const [name, legacy] of [['empty', []], ['legacy', ['转场日无需专门安排拍摄。']]]) {
      const noPlan = structuredClone(G);
      noPlan.days[0].photoPlan = []; noPlan.days[0].shooting = legacy; noPlan.days[0].photo = '';
      const empty = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
      empty.on('pageerror', e => report.errors.push(e.message));
      await empty.route(/^https?:/, r => r.request().url() === 'https://copy.test/photo-' + name ? r.fulfill({ contentType: 'text/html', body: withGuide(noPlan) }) : r.abort());
      await empty.goto('https://copy.test/photo-' + name); await empty.locator('#pocket-open').click();
      await empty.locator('dialog[open] .tool-day-nav [data-day="0"]').click();
      await empty.locator('dialog[open] .tool-section-nav [data-tool="photos"]').click();
      await empty.locator('#reference-upload').waitFor({ state: 'visible' });
      await checkPhotoCopy(empty, noPlan.days[0]);
      await empty.locator('dialog[open] .tool-section-nav [data-open-pocket]').click();
      assert(await empty.locator('#pocket-dialog').isVisible(), 'No-plan day must retain tool switching');
      await empty.close();
    }
    report.checks.push('Independent zero-photo and legacy-note fixtures keep uploads and tool switching available; no minimum plan imposed by the browser check');

    // The international example must not label one map service while opening another.
    const K = structuredClone(G); K.edition.lang = 'ko'; K.edition.slug = 'qa-korean-map-copy';
    const fixture = withGuide(K);
    const q = await browser.newPage({ reducedMotion: 'reduce' });
    q.on('pageerror', e => report.errors.push(e.message));
    await q.route(/^https?:/, r => r.request().url() === 'https://copy.test/korean' ? r.fulfill({ contentType: 'text/html', body: fixture }) : r.abort());
    await q.goto('https://copy.test/korean'); await q.locator('#pocket-open').click();
    assert.deepEqual(await q.locator('#map-provider option').allTextContents(), ['Naver 地图', 'Kakao 地图']);
    assert((await q.locator('.pocket-navigate').first().getAttribute('href')).startsWith('https://map.naver.com/'));
    await q.locator('#map-provider').selectOption('apple');
    assert((await q.locator('.pocket-navigate').first().getAttribute('href')).startsWith('https://map.kakao.com/'));
    report.checks.push('Korean map labels match their existing navigation targets; stored provider preferences remain compatible');
    await q.close();
    assert.deepEqual(report.errors, []); report.result = 'pass';
    console.log('PASS travel copy, local-file failure states and international provider labels');
  } catch (error) { report.result = 'fail'; report.failure = String(error); throw error; }
  finally { await browser.close(); fs.writeFileSync(path.join(qa, 'report.json'), JSON.stringify(report, null, 2)); }
})().catch(error => { console.error(error); process.exit(1); });
