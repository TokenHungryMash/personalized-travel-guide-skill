/* Readability checks for language controls and the retained four-tool ledger flow. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto'),{pathToFileURL}=require('url');
const root=path.resolve(process.argv[2]),{chromium,executablePath}=require('./browser_runtime.cjs').browserRuntime(root),m=JSON.parse(fs.readFileSync(path.join(root,'build-manifest.json'))),dir=path.join(root,'qa-readability');fs.mkdirSync(dir,{recursive:true});
const html=path.join(root,m.artifact),report={result:'pending',buildId:m.buildId,sha256:m.sha256,checks:[],errors:[]};assert.equal(crypto.createHash('sha256').update(fs.readFileSync(html)).digest('hex'),m.sha256);
async function target44(locator){const box=await locator.boundingBox();assert(box&&box.height>=43.5&&box.width>=43.5,'Disclosure must provide a 44px target')}
const englishOnly=/^en(?:-|$)/i.test(JSON.parse(fs.readFileSync(path.join(root,'edition.json'))).lang),languages=englishOnly?['local']:['local','english'];
(async()=>{const b=await chromium.launch({executablePath});try{
 const p=await b.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});p.on('pageerror',e=>report.errors.push(e.message));await p.route(/^https?:/,r=>r.abort());await p.goto(pathToFileURL(html).href);await p.evaluate(()=>document.fonts.ready);
 const key=await p.locator('#guide-data').evaluate(e=>'travel-magazine-v4-'+JSON.parse(e.textContent).edition.slug);
 for(const width of [320,390,768,1440]){
  await p.setViewportSize({width,height:width===1440?1000:844});
  for(const surface of ['main','pocket']){
   if(surface==='pocket'){
    await p.locator('#pocket-open').click();assert.equal(await p.locator('#pocket-dialog .tool-section-nav button').count(),4);assert.equal(await p.locator('.tool-section-nav [data-tool=files]').count(),0);assert(await p.locator('#pocket-dialog [data-attach-stop]').count()>0);
    await p.locator('#pocket-dialog [data-reference=language]').click();
   }
   const scope=p.locator(surface==='main'?'#language-content':'#travel-reference-body'),wb=surface==='main'?scope:scope.locator('[data-language-workbench]');
   if(!englishOnly)await wb.locator('[data-language-mode=local]').click();const scene=await wb.locator('[data-language-panel]:has(.phrase)').first().getAttribute('data-language-panel');await wb.locator('[data-language-scene="'+scene+'"]').click();
   const panel=wb.locator('section[data-language-panel]:not([hidden])');await panel.locator('[data-language-view=phrases]').click();
   const pane=panel.locator('div[data-language-pane=phrases]'),help=pane.locator('details.phrase-help').first();
   if(await help.count()){const summary=help.locator(':scope>summary');await target44(summary);
   assert(await summary.evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=14),'Disclosure label must stay readable');
   if(await help.evaluate(e=>e.open))await summary.click();await summary.click();assert(await help.evaluate(e=>e.open),'Usage disclosure must open on a real click');await summary.click();assert.equal(await help.evaluate(e=>e.open),false);}
   const fieldFold=pane.locator('details.phrase-fields').first();if(await fieldFold.count()){
    const fieldSummary=fieldFold.locator(':scope>summary');await target44(fieldSummary);
    if(!(await fieldFold.evaluate(e=>e.open)))await fieldSummary.click();assert(await fieldFold.locator('[data-phrase-input=local]').isVisible(),'Required ingredient must be reachable through its disclosure');
    await fieldSummary.click();assert.equal(await fieldFold.evaluate(e=>e.open),false);
   }
   for(const lang of languages){
    if(!englishOnly)await wb.locator('[data-language-mode='+lang+']').click();
    assert(await pane.locator('[data-language-text='+lang+']:visible').first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=16));
    assert(await scope.evaluate(e=>e.scrollWidth<=e.clientWidth+1),surface+' language overflow '+width);if(surface==='pocket')await scope.evaluate(e=>e.scrollTop=0);else await wb.evaluate(e=>window.scrollTo(0,window.scrollY+e.getBoundingClientRect().top-120));
    await p.waitForTimeout(650);await p.screenshot({path:path.join(dir,['language',surface,lang,width].join('-')+'.png')});
   }
   if(surface==='pocket'){await p.locator('#travel-reference-dialog [data-close]').click();await p.locator('#pocket-dialog [data-close]').click()}
  }
 }
 report.checks.push('Main and pocket language: real disclosure clicks, 44px targets, readable local/English text at 320/390/768/1440');
 await p.setViewportSize({width:390,height:844});await p.locator('#pocket-open').click();await p.locator('#pocket-dialog [data-tool=ledger]').click();
 await p.locator('#trip-budget').fill('6,000,000');await p.locator('#trip-budget').blur();assert.equal(await p.locator('#trip-budget').inputValue(),'6,000,000');assert.equal(await p.evaluate(k=>JSON.parse(localStorage.getItem(k)).budget,key),6000000);
 await p.locator('#expense-form [name=title]').fill('金额分隔验证');await p.locator('#expense-form [name=amount]').fill('1,234');await p.locator('#expense-form [type=submit]').click();assert.equal(await p.evaluate(k=>JSON.parse(localStorage.getItem(k)).expenses.at(-1).amount,key),1234);
 await p.locator('#expense-form [name=title]').fill('小数金额验证');await p.locator('#expense-currency').selectOption('USD');await p.locator('#expense-form [name=amount]').fill('12,345.67');await p.locator('#expense-form [type=submit]').click();assert.equal(await p.evaluate(k=>JSON.parse(localStorage.getItem(k)).expenses.at(-1).amount,key),12345.67);
 assert(await p.evaluate(()=>Number.isNaN(MagazineLedger.parseAmount('1,2'))));await p.reload();await p.locator('#pocket-open').click();await p.locator('#pocket-dialog [data-tool=ledger]').click();assert.equal(await p.locator('#trip-budget').inputValue(),'6,000,000');
 for(const width of [320,390,768,1440]){await p.setViewportSize({width,height:width===1440?1000:844});assert(await p.locator('#pocket-dialog').evaluate(e=>e.scrollWidth<=e.clientWidth+1),'Ledger dialog overflow '+width);await p.waitForTimeout(650);await p.screenshot({path:path.join(dir,'ledger-'+width+'.png')})}
 report.checks.push('Four primary tools and stop attachments retained; comma-grouped budget and expense amounts, decimal currency, invalid grouping and reload');
 assert.deepEqual(report.errors,[]);report.result='pass';console.log('PASS compact language disclosures, four tools, grouped amounts and reload');
}catch(e){report.result='fail';report.failure=e.stack;throw e}finally{fs.writeFileSync(path.join(dir,'report.json'),JSON.stringify(report,null,2));await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
