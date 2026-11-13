const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');const {browserRuntime}=require('./browser_runtime.cjs');
const root=path.resolve(process.argv[2]||'.');
(async()=>{const manifest=JSON.parse(fs.readFileSync(path.join(root,'build-manifest.json'),'utf8'));const {chromium,executablePath}=browserRuntime(root);const browser=await chromium.launch({executablePath,headless:true});
try{for(const width of [589,390,320]){const page=await browser.newPage({viewport:{width,height:900},reducedMotion:'reduce'});await page.goto(pathToFileURL(path.join(root,manifest.artifact)).href);await page.evaluate(()=>document.fonts.ready);
const rows=await page.locator('#place-results .address-card').evaluateAll(cards=>cards.map(card=>{const r=e=>{const b=e.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width}};return {card:r(card),copy:r(card.querySelector('.directory-description')),actions:r(card.querySelector('.directory-actions'))}}));assert(rows.length,'No rendered cards');
for(const row of rows){assert(row.copy.width>=row.card.width-4,`Body remains trapped beside thumbnail at ${width}px`);assert(row.actions.top>=row.copy.bottom-1,`Actions overlap body at ${width}px`)}
assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);await page.close();}console.log('PASS directory body width and action placement at 589/390/320.');}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
