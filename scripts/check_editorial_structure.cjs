/* Regression: city/region reading must be independent, navigation and both TOCs must agree. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto'),{pathToFileURL}=require('url');
const R=path.resolve(process.argv[2]||'.'),{chromium,executablePath}=require('./browser_runtime.cjs').browserRuntime(R);
const manifest=JSON.parse(fs.readFileSync(path.join(R,'build-manifest.json'))),editorial=JSON.parse(fs.readFileSync(path.join(R,'editorial-content.json')));
const artifact=path.join(R,manifest.artifact),html=fs.readFileSync(artifact);assert.equal(crypto.createHash('sha256').update(html).digest('hex'),manifest.sha256);
const qa=path.join(R,'qa-editorial-structure');fs.mkdirSync(qa,{recursive:true});
const report={buildId:manifest.buildId,sha256:manifest.sha256,result:'pending',errors:[],contrast:[],checks:[]};
(async()=>{const b=await chromium.launch({executablePath,headless:true});try{
 const p=await b.newPage({reducedMotion:'reduce'});p.on('pageerror',e=>report.errors.push(e.message));await p.route(/^https?:/,r=>r.abort());await p.goto(pathToFileURL(artifact).href);await p.evaluate(()=>document.fonts.ready);
 const order=await p.locator('main>.chapter').evaluateAll(els=>els.map(e=>e.id));assert.deepEqual(order.slice(0,4),['orientation','neighbourhoods','itinerary','food']);
 for(const selector of ['.journal-contents .toc-entry','#menu-dialog .toc-entry'])assert.deepEqual(await p.locator(selector).evaluateAll(els=>els.map(e=>e.hash.slice(1))),order);
 assert.equal(await p.locator('#journey-overview').evaluate(e=>e.closest('.chapter').id),'itinerary');
 const lead=await p.locator('#orientation').innerText();assert(!/第\s*[0-9一二三四五六七八九十]+\s*天|DAY\s*\d+/i.test(lead),'City/lodging text contains a day-by-day plan');
 for(const [id,rows] of Object.entries(editorial.area_sections||{}))assert.equal(await p.locator('#area-'+id+' .district-section').count(),rows.length,'Missing regional prose '+id);
 const rowSources=Object.values(editorial.section_sources||{}).flatMap(Object.values).reduce((n,ids)=>n+ids.length,0);
 const cardSources=[...(editorial.preparation||[]),...(editorial.restaurant_groups||[])].flatMap(g=>g.items).reduce((n,item)=>n+(item.sources||[]).length,0);
 assert.equal(await p.locator('main .editorial-source-links a').count(),rowSources+cardSources,'Source links missing from rendered text');
 async function contrast(selector){return p.locator(selector).evaluateAll(els=>els.map(e=>{
  const parse=s=>s.match(/[\d.]+/g).map(Number),luma=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
  let n=e,bg;while(n){const c=parse(getComputedStyle(n).backgroundColor);if(c.length<4||c[3]===1){bg=c;break}n=n.parentElement}bg=bg||[255,255,255];const style=getComputedStyle(e),fg=parse(style.color),a=luma(fg),bb=luma(bg);return {text:e.textContent,ratio:(Math.max(a,bb)+.05)/(Math.min(a,bb)+.05),opacity:style.opacity,fontSize:style.fontSize};
 }));}
 for(const width of [320,390,1440]){
  await p.setViewportSize({width,height:width<700?844:1000});
  for(const [name,sel] of [['city','#orientation .city-portrait'],['region','#neighbourhoods .area-introduction'],['lodging','#orientation .subheading']]){
   await p.locator(sel).first().evaluate(e=>{e.scrollIntoView({behavior:'instant'});scrollBy(0,-145)});await p.waitForTimeout(80);assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Overflow '+name+width);await p.screenshot({path:path.join(qa,name+'-'+width+'.png')});
  }
  await p.locator('.journal-contents').evaluate(e=>e.scrollIntoView({behavior:'instant'}));const dark=await contrast('.journal-contents .toc-copy small');assert(dark.every(c=>c.ratio>=4.5&&Number(c.opacity)===1),'Dark TOC contrast');
  await p.locator('#menu-open').click();const light=await contrast('#menu-dialog .toc-copy small');assert(light.every(c=>c.ratio>=4.5&&Number(c.opacity)===1),'Light TOC contrast');report.contrast.push({width,darkMinimum:Math.min(...dark.map(x=>x.ratio)),lightMinimum:Math.min(...light.map(x=>x.ratio))});await p.screenshot({path:path.join(qa,'menu-'+width+'.png')});await p.locator('#menu-dialog [data-close]').click();
 }
 await p.setViewportSize({width:1440,height:1000});await p.locator('#itinerary').evaluate(e=>e.scrollIntoView({behavior:'instant'}));await p.locator('#day-tabs [data-day]').last().click();assert.equal(await p.locator('.day-continuation a').getAttribute('href'),'#food');
 assert.deepEqual(report.errors,[]);report.checks=['City → regions → itinerary; both TOCs and chapter numbering agree','Overview in itinerary; city and lodging independent of trip days','Every authored district paragraph and nearby source rendered','Light/dark TOC text contrast at 320/390/1440','Last itinerary day continues forward to food'];report.result='pass';console.log('PASS editorial structure and TOC contrast:',manifest.buildId);
}finally{await b.close();fs.writeFileSync(path.join(qa,'report.json'),JSON.stringify(report,null,2))}})().catch(e=>{report.result='fail';report.failure=String(e);fs.writeFileSync(path.join(qa,'report.json'),JSON.stringify(report,null,2));console.error(e);process.exit(1)});
