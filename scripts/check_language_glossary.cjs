/* Exercise every authored language scene, view and language on both reader surfaces. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto'),{pathToFileURL}=require('url');
const root=path.resolve(process.argv[2]),m=JSON.parse(fs.readFileSync(path.join(root,'build-manifest.json'))),t=JSON.parse(fs.readFileSync(path.join(root,'editorial-content.json')));
const html=path.join(root,m.artifact),{chromium,executablePath}=require('./browser_runtime.cjs').browserRuntime(root),out=path.join(root,'qa-language-glossary');
fs.mkdirSync(out,{recursive:true});assert.equal(crypto.createHash('sha256').update(fs.readFileSync(html)).digest('hex'),m.sha256,'QA must use the current manifest artifact');
const scenes=t.languageScenes,groups=Object.entries(t.words).filter(([k])=>k.startsWith('常备 · ')),report={result:'pending',buildId:m.buildId,sha256:m.sha256,scenes:scenes?.length,terms:groups.reduce((n,[,v])=>n+v.length,0),visits:[],errors:[]};
const compact=value=>value.replace(/\s+/g,' ').trim();
const authored=(scene,view)=>view==='phrases'?(t.phrases[scene.phrases]||[]):(t.words[scene[view]]||[]);
async function assertTarget(locator,label){
 const box=await locator.boundingBox();assert(box&&box.width>=43.5&&box.height>=43.5,label+' must provide a 44px target');
 assert(await locator.evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=14),label+' must not use tiny text');
}
const englishOnly=/^en(?:-|$)/i.test(JSON.parse(fs.readFileSync(path.join(root,'edition.json'))).lang),languages=englishOnly?['local']:['local','english'];
(async()=>{
 const browser=await chromium.launch({executablePath});
 try{
  assert(Array.isArray(scenes)&&scenes.length,'Authored languageScenes are required');
  assert.equal(new Set(scenes.map(s=>s.id)).size,scenes.length,'Scene IDs must be unique');
  const p=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
  p.on('pageerror',e=>report.errors.push(e.message));await p.route(/^https?:/,r=>r.abort());
  await p.goto(pathToFileURL(html).href);await p.evaluate(()=>document.fonts.ready);
  for(const width of [320,390,768,1440]){
   await p.setViewportSize({width,height:width===1440?1000:844});
   for(const surface of ['main','pocket']){
    if(surface==='pocket'){await p.locator('#pocket-open').click();await p.locator('#pocket-dialog [data-reference=language]').click()}
    const scope=p.locator(surface==='main'?'#language-content':'#travel-reference-body'),workbench=surface==='main'?scope:scope.locator('[data-language-workbench]');
    assert.equal(await workbench.count(),1);assert.equal(await workbench.locator('[data-language-scene]').count(),scenes.length);
    assert.equal(await scope.locator('.phrase').count(),Object.values(t.phrases).flat().length,'All authored phrases must remain available');
    if(surface==='pocket')assert.equal(await scope.locator('[id]').count(),0,'Reference clones must not duplicate IDs');
    for(const scene of scenes){
     const sceneButton=workbench.locator('[data-language-scene="'+scene.id+'"]');
     await sceneButton.click();await assertTarget(sceneButton,scene.id+' scene');assert.equal(await sceneButton.getAttribute('aria-pressed'),'true');
     assert.equal(await workbench.locator('[data-language-scene][aria-pressed=true]').count(),1);
     const sceneLayout=await sceneButton.evaluate(e=>{
      const range=document.createRange();range.selectNodeContents(e);
      const lines=[...new Set([...range.getClientRects()].filter(r=>r.width&&r.height).map(r=>Math.round(r.top)))].length;
      const rect=e.getBoundingClientRect(),row=[...e.parentElement.querySelectorAll('[data-language-scene]')].map(b=>b.getBoundingClientRect()).filter(r=>Math.abs(r.top-rect.top)<2);
      return {label:e.textContent.trim(),lines,heights:row.map(r=>r.height)};
     });
     if(/^[\u4e00-\u9fff]{1,4}$/.test(sceneLayout.label))assert.equal(sceneLayout.lines,1,'A short scene label must fit on one line: '+sceneLayout.label+' '+surface+' '+width);
     assert(Math.max(...sceneLayout.heights)-Math.min(...sceneLayout.heights)<1.5,'Scene buttons sharing a row must have consistent heights');

     const panel=workbench.locator('section[data-language-panel="'+scene.id+'"]');
     assert(await panel.isVisible());assert.equal(await workbench.locator('section[data-language-panel]:not([hidden])').count(),1,'Only the selected scene should occupy space');
     for(const language of languages){
      const mode=workbench.locator('[data-language-mode="'+language+'"]');if(!englishOnly){await mode.click();await assertTarget(mode,language+' switch')}
      assert.equal(await workbench.getAttribute('data-language'),language);if(!englishOnly)assert.equal(await mode.getAttribute('aria-pressed'),'true');else assert.equal(await workbench.locator('[data-language-mode],[data-language-text=english],[data-phrase-input=english]').count(),0);
      for(const view of ['phrases','glossary','replies']){
       const rows=authored(scene,view),tab=panel.locator('[data-language-view="'+view+'"]');
       if(!rows.length){assert(!(await tab.count())||!(await tab.isVisible())||await tab.isDisabled(),scene.id+' must not advertise an empty '+view+' view');continue}
       assert.equal(await tab.count(),1,scene.id+' '+view+' tab');await tab.click();await assertTarget(tab,scene.id+' '+view+' tab');assert.equal(await tab.getAttribute('aria-pressed'),'true');
       const pane=panel.locator('div[data-language-pane="'+view+'"]');assert(await pane.isVisible());
       assert.equal(await panel.locator('div[data-language-pane]:not([hidden])').count(),1,'Only the selected view should occupy space');
       const actual=compact(await pane.innerText());
       for(const row of rows){
        const expected=Array.isArray(row)?row[0]:row[language==='english'?'english':'local'];
        assert(expected,scene.id+' '+view+' lacks authored '+language+' content');assert(actual.includes(compact(expected)),scene.id+' '+view+' '+language+' missing '+expected);
       }
       const spans=pane.locator('[data-language-text="'+language+'"]:visible');assert(await spans.count()>0,'Selected-language text must be visible');
       assert.equal(await pane.locator('[data-language-text="'+(language==='english'?'local':'english')+'"]:visible').count(),0,'The other language must not be stacked beneath the selected one');
       const small=await spans.evaluateAll(es=>es.filter(e=>parseFloat(getComputedStyle(e).fontSize)<16).map(e=>({text:e.textContent,size:getComputedStyle(e).fontSize})));assert.deepEqual(small,[],'Language text must be at least 16px');
       for(const area of [scope,panel,pane])assert(await area.evaluate(e=>e.scrollWidth<=e.clientWidth+1),surface+' '+width+' '+scene.id+' '+view+' overflow');
       assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Page overflow at '+width);
       report.visits.push({surface,width,scene:scene.id,language,view,rows:rows.length});
       if(scene.id===scenes[0].id&&['phrases','glossary'].includes(view)){
        if(surface==='pocket')await scope.evaluate(e=>e.scrollTop=0);else await workbench.evaluate(e=>window.scrollTo(0,window.scrollY+e.getBoundingClientRect().top-120));await p.waitForTimeout(650);await p.screenshot({path:path.join(out,[surface,width,language,view].join('-')+'.png')});
       }
      }
     }
    }
    if(surface==='pocket'){await p.locator('#travel-reference-dialog [data-close]').click();await p.locator('#pocket-dialog [data-close]').click()}
   }
  }
  assert.deepEqual(report.errors,[]);report.result='pass';console.log('PASS '+report.visits.length+' language states: all scenes/views/languages, both surfaces, four widths');
 }catch(e){report.result='fail';report.failure=e.stack;throw e}
 finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
