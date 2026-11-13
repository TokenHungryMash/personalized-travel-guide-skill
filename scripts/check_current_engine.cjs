/* Real-browser contract for every new-city workbench, including offline files. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto'),{pathToFileURL}=require('url');
const R=path.resolve(process.argv[2]||'.');
const {chromium,executablePath}=require('./browser_runtime.cjs').browserRuntime(R);
const m=JSON.parse(fs.readFileSync(path.join(R,'build-manifest.json'))),html=fs.readFileSync(path.join(R,m.artifact),'utf8'),qa=path.join(R,'qa-current-engine');fs.mkdirSync(qa,{recursive:true});
assert.equal(crypto.createHash('sha256').update(html).digest('hex'),m.sha256,'Standalone HTML does not match build-manifest.json. Run python -X utf8 build.py in the workbench and rerun this check.');
const report={buildId:m.buildId,sha256:m.sha256,result:'pending',checks:[],errors:[]};
(async()=>{const browser=await chromium.launch({executablePath,headless:true});try{
 const p=await browser.newPage({reducedMotion:'reduce',acceptDownloads:true});p.setDefaultTimeout(10000);p.on('pageerror',e=>report.errors.push(e.message));p.on('dialog',d=>d.accept());await p.route(/^https?:/,r=>r.abort());
 await p.goto(pathToFileURL(path.join(R,m.artifact)).href);await p.evaluate(()=>document.fonts.ready);
 const G=await p.locator('#guide-data').evaluate(e=>JSON.parse(e.textContent)),N=G.days.length,key='travel-magazine-v4-'+G.edition.slug;
 const state=()=>p.evaluate(k=>JSON.parse(localStorage.getItem(k)),key);
 async function choose(i){const dock=p.locator('.mobile-day-dock');if(await dock.isVisible()){if(await dock.locator('select').count())await dock.locator('select').selectOption(String(i));else await dock.locator('[data-day="'+i+'"]').click();}else await p.locator('#day-tabs [data-day="'+i+'"]').click();await p.waitForTimeout(60);}
 for(const width of [320,390,1440]){
  await p.setViewportSize({width,height:width===1440?900:844});await p.evaluate(()=>scrollTo(0,0));await p.waitForTimeout(60);
  assert(await p.locator('.overprint-cover').isVisible());assert(await p.locator('.journal-finale').evaluate(e=>{const photo=e.querySelector('.closing-photo').getBoundingClientRect(),copy=e.querySelector('.closing-copy').getBoundingClientRect();return photo.width>=Math.min(innerWidth,1800)-5&&copy.top>=photo.bottom}),'Finale must not collapse into legacy columns');assert(await p.locator('#cover-film').evaluate(e=>e.naturalWidth>0&&e.getBoundingClientRect().height>400));
  assert(await p.locator('#cover-title').evaluate(e=>e.getBoundingClientRect().right<=innerWidth),'Cover title overflow');await p.screenshot({path:path.join(qa,'cover-'+width+'.png')});
  for(const id of ['orientation','itinerary','neighbourhoods','food','culture','shopping','fieldnotes','prepare','directory','tools']){
   await p.locator('#'+id).evaluate(e=>e.scrollIntoView({behavior:'instant'}));await p.waitForFunction(expected=>document.querySelector('.reading-actions')?.dataset.context===expected,id,{timeout:2000});assert.equal(await p.locator('.reading-actions').getAttribute('data-context'),id);assert(await p.locator('.context-scroll').locator('a,button').count()>0);
  }
  await p.locator('#itinerary').evaluate(e=>e.scrollIntoView({behavior:'instant'}));await p.waitForTimeout(60);
  if(width<701){assert(await p.locator('.mobile-day-dock').isVisible());assert(!await p.locator('#day-tabs').isVisible());if(N<=7)assert.equal(await p.locator('.mobile-day-dock button').count(),N);else assert.equal(await p.locator('.mobile-day-dock option').count(),N);}
  for(let i=0;i<N;i++){await choose(i);assert.equal((await state()).day,i);assert.equal(await p.locator('[data-next-day]').count(),i===N-1?0:1);}
  await choose(0);await p.locator('[data-next-day]').click();assert.equal((await state()).day,1);
  await p.locator('#pocket-open').click();assert(!await p.locator('.mobile-day-dock').isVisible());
  for(let i=0;i<N;i++){
   await p.locator('#pocket-dialog .tool-day-nav [data-day="'+i+'"]').click();const options=p.locator('.alternative-option');assert.equal(await options.count(),G.days[i].alternatives.length);await p.locator('.pocket-alternatives>summary').click();await options.first().locator('summary').click();assert(await options.first().locator('.alternative-body').isVisible());if(width<701)assert(await p.locator('.pocket-alternatives').evaluate(e=>e.getBoundingClientRect().width>=innerWidth-45),'Opened alternatives must use the full mobile column');
   const before=await state();const link=options.first().locator('[data-place]').first();if(await link.count()){await link.click();assert(await p.locator('#place-dialog').isVisible());await p.locator('#place-dialog [data-close]').click();assert(await p.locator('#pocket-dialog').isVisible());assert(await options.first().locator('.alternative-body').isVisible());}
   assert.deepEqual((await state()).custom,before.custom);assert.equal((await state()).day,i);assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   if(i===1)await p.screenshot({path:path.join(qa,'alternatives-'+width+'.png')});
  }
  await p.locator('#pocket-dialog [data-close]').click();
 }
 report.checks.push('320/390/1440: full photo cover, ten contextual navigations, all dates, next-day/final exit; per-day alternatives and nested place return do not alter routes');
 // Real uploads, persisted state and both backup generations.
 await p.setViewportSize({width:390,height:844});await p.locator('#pocket-open').click();await p.locator('#pocket-dialog [data-tool=ledger]').click();await p.locator('.ledger-member-fold').evaluate(e=>e.open=true);
 const avatarFixture=await p.evaluate(async()=>{const image=document.querySelector('.edition-plate img');await image.decode();const canvas=document.createElement('canvas');canvas.width=512;canvas.height=512;canvas.getContext('2d').drawImage(image,0,0,512,512);return canvas.toDataURL('image/jpeg',0.85).split(',')[1]});await p.locator('[data-member-avatar="我"]').setInputFiles({name:'avatar-fixture.jpg',mimeType:'image/jpeg',buffer:Buffer.from(avatarFixture,'base64')});await p.waitForFunction(k=>!!JSON.parse(localStorage.getItem(k)).memberAvatars?.['我'],key);const avatar=(await state()).memberAvatars['我'];assert(avatar.length<32000);assert(await p.locator('#members-list img').evaluate(e=>e.naturalWidth===128));
 await p.locator('#ledger-dialog [data-close]').click();await p.reload();assert.equal((await state()).memberAvatars['我'],avatar);
 const dp=p.waitForEvent('download');await p.locator('#export-data').click();const download=await dp,backup=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.equal(backup.state.memberAvatars['我'],avatar);const old=structuredClone(backup);delete old.state.memberAvatars;
 await p.locator('#import-data').setInputFiles({name:'old.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(old))});await p.waitForFunction(k=>!JSON.parse(localStorage.getItem(k)).memberAvatars,key);await p.locator('#import-data').setInputFiles({name:'new.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(backup))});await p.waitForFunction(k=>!!JSON.parse(localStorage.getItem(k)).memberAvatars?.['我'],key);
 report.checks.push('Avatar upload, 128px compression, reload, backup export, legacy import and avatar backup import');
 // Test layout invariants with 3/10-day fixtures and a long city name, never published.
 for(const count of [3,10]){
  const ctx=await browser.newContext({viewport:{width:320,height:844},reducedMotion:'reduce'}),q=await ctx.newPage();q.on('pageerror',e=>report.errors.push(e.message));
  const fixture=structuredClone(G);fixture.days=Array.from({length:count},(_,i)=>structuredClone(G.days[i%N]));fixture.edition.english='CHIANG MAI';
  const sample=html.replace(/(<script id="guide-data" type="application\/json">)[\s\S]*?(<\/script>)/,(all,a,b)=>a+JSON.stringify(fixture).replace(/<\//g,'<\\/')+b).replace(/(id="cover-title">)[^<]+/,'$1CHIANG MAI').replace(/--cover-title-vw:[\d.]+vw/g,'--cover-title-vw:11vw').replace(/--cover-title-mobile:[\d.]+vw/g,'--cover-title-mobile:13vw');
  await q.route('https://layout.test/**',r=>r.fulfill({contentType:'text/html',body:sample}));await q.goto('https://layout.test/'+count);await q.evaluate(()=>document.fonts.ready);assert(await q.locator('#cover-title').evaluate(e=>e.getBoundingClientRect().right<=innerWidth));
  await q.locator('#itinerary').evaluate(e=>e.scrollIntoView({behavior:'instant'}));await q.waitForTimeout(80);const dock=q.locator('.mobile-day-dock');assert(await dock.isVisible());assert.equal(await q.locator('#day-tabs button>span').last().textContent(),String(count).padStart(2,'0'),'Day number must not become 010');
  if(count<=7){assert.equal(await dock.locator('button').count(),count);await dock.locator('[data-day="2"]').click();}else{assert.equal(await dock.locator('option').count(),count);await dock.locator('select').selectOption('9');assert(await dock.locator('[data-step="1"]').isDisabled());await dock.locator('[data-step="-1"]').click();assert.equal(await dock.locator('select').inputValue(),'8');}
  assert(await q.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await ctx.close();
 }
 report.checks.push('Additional 3/10-day and long-city-name fixtures: variable dock, accessible selector, last-day boundaries');assert.deepEqual(report.errors,[]);report.result='pass';console.log('PASS current-engine contract:',G.edition.city,N,'days');
 }finally{await browser.close();fs.writeFileSync(path.join(qa,'report.json'),JSON.stringify(report,null,2));}})().catch(e=>{report.result='fail';report.error=String(e);fs.writeFileSync(path.join(qa,'report.json'),JSON.stringify(report,null,2));console.error(e);process.exit(1)});
