/* Shared dining/checklist regressions and bilingual language fields with real backup recovery. */
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto'),{pathToFileURL}=require('url');
const root=path.resolve(process.argv[2]||'.'),m=JSON.parse(fs.readFileSync(path.join(root,'build-manifest.json'))),t=JSON.parse(fs.readFileSync(path.join(root,'editorial-content.json')));
const html=path.join(root,m.artifact);assert.equal(crypto.createHash('sha256').update(fs.readFileSync(html)).digest('hex'),m.sha256);
const {chromium,executablePath}=require('./browser_runtime.cjs').browserRuntime(root),dir=path.join(root,'qa-reader-reference');fs.mkdirSync(dir,{recursive:true});
const report={result:'pending',buildId:m.buildId,sha256:m.sha256,checks:[],errors:[]};
const englishOnly=/^en(?:-|$)/i.test(JSON.parse(fs.readFileSync(path.join(root,'edition.json'))).lang),languages=englishOnly?['local']:['local','english'];
(async()=>{const browser=await chromium.launch({executablePath});try{
 const p=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce',acceptDownloads:true});p.on('pageerror',e=>report.errors.push(e.message));await p.route(/^https?:/,r=>r.abort());await p.goto(pathToFileURL(html).href);await p.evaluate(()=>document.fonts.ready);
 const G=await p.locator('#guide-data').evaluate(e=>JSON.parse(e.textContent)),key='travel-magazine-v4-'+G.edition.slug;
 const tasks=t.preparation?.flatMap(g=>g.items),first=tasks?.find(x=>x.id==='c0')?.id||await p.locator('#preparation-content [data-check]').first().getAttribute('data-check'),extra=tasks?.find(x=>x.id!==first&&x.id.startsWith('prep-'))?.id;
 await p.evaluate(({key,first})=>{const state=JSON.parse(localStorage.getItem(key));state.checks=[first];state.notes.qaReference='keep my notes';localStorage.setItem(key,JSON.stringify(state))},{key,first});await p.reload();
 assert.equal(await p.locator('#preparation-content [data-check="'+first+'"]').isChecked(),true);assert.equal(await p.evaluate(key=>JSON.parse(localStorage.getItem(key)).notes.qaReference,key),'keep my notes');
 assert.deepEqual(await p.locator('#restaurant-guide .restaurant-group>header h3').evaluateAll(es=>es.map(e=>e.childNodes[0].textContent.trim())),t.restaurant_groups.map(g=>g.name));
 await p.locator('#pocket-open').click();assert.equal(await p.locator('#pocket-dialog [data-reference=preparation]').count(),0);
 for(let day=0;day<G.days.length;day++){
  await p.locator('#pocket-dialog .tool-day-nav [data-day="'+day+'"]').click();const expected=G.days[day].dining||[];if(!expected.length)continue;
  const fold=p.locator('.pocket-dining');await fold.locator(':scope>summary').click();assert.equal(await fold.locator('.dining-shortlist>button').count(),expected.length);
  await fold.locator('.dining-shortlist>button').first().click();assert(await p.locator('#pocket-dialog').isVisible());assert(await p.locator('#travel-reference-dialog').isVisible());
  assert.deepEqual(await p.locator('#travel-reference-body [data-restaurant-id]').evaluateAll(es=>es.map(e=>e.dataset.restaurantId).sort()),[...expected].sort());
  const card=p.locator('#travel-reference-body [data-restaurant-id="'+expected[0]+'"]');assert(await card.evaluate(e=>e.open));
  assert.equal((await card.textContent()).replace(/\s+/g,''),(await p.locator('#eat-'+expected[0]).textContent()).replace(/\s+/g,''));
  await card.locator('[data-place]').click();await p.locator('#place-dialog [data-close]').click();assert(await card.evaluate(e=>e.open));
  await p.locator('[data-reference-all=true]').click();assert.equal(await p.locator('#travel-reference-body .restaurant-pick').count(),t.restaurant_groups.flatMap(g=>g.items).length);
  await p.locator('#travel-reference-dialog [data-close]').click();assert(await fold.evaluate(e=>e.open));
 }
 report.checks.push('All days: dining candidates match authored references, cloned facts equal main text, place return and all-restaurants view');
 await p.locator('#pocket-dialog .travel-body').evaluate(e=>e.scrollTop=0);await p.locator('#pocket-dialog [data-reference=language]').click();await p.locator('#travel-reference-dialog [data-reference=preparation]').click();
 assert.equal(await p.locator('#travel-reference-body [id]').count(),0,'Cloned content must not duplicate IDs');assert(await p.locator('#travel-reference-body [data-check="'+first+'"]').isChecked());
 if(extra){await p.locator('#travel-reference-body [data-check="'+extra+'"]').check();assert(await p.locator('#preparation-content [data-check="'+extra+'"]').isChecked());assert((await p.locator('#travel-reference-body [data-check-count]').innerText()).includes('2 / '+tasks.length))}
 const phrases=Object.values(t.phrases).flat(),scenes=t.languageScenes;
 const wb=scope=>p.locator(scope==='#language-content'?scope:scope+' [data-language-workbench]');
 const activate=async(scope,scene,language)=>{await wb(scope).locator('[data-language-scene="'+scene+'"]').click();if(!englishOnly)await wb(scope).locator('[data-language-mode='+language+']').click();await wb(scope).locator('section[data-language-panel="'+scene+'"] [data-language-view=phrases]').click()};
 const openFields=async card=>{const fold=card.locator('details.phrase-fields');if(await fold.count()&&!(await fold.evaluate(e=>e.open)))await fold.locator(':scope>summary').click()};
 await p.locator('#travel-reference-dialog .travel-reference-nav [data-reference=language]').click();assert.equal(await p.locator('#travel-reference-body .phrase').count(),phrases.length);
 const initialScene=scenes.find(s=>s.phrases&&t.phrases[s.phrases]?.length);await activate('#travel-reference-body',initialScene.id,'local');
 const firstPhrase=p.locator('#travel-reference-body section[data-language-panel="'+initialScene.id+'"] .phrase').first();await firstPhrase.click();assert(await p.locator('#phrase-dialog').isVisible());assert.equal(await p.locator('#phrase-big h2').innerText(),await firstPhrase.getAttribute('data-jp'));await p.locator('#phrase-dialog [data-close]').click();assert(await p.locator('#travel-reference-dialog').isVisible());
 let phraseCase=null;
 const authored=phrases.find(row=>!Array.isArray(row)&&row.input?.required);
 if(authored){
  const id=authored.id,scene=scenes.find(s=>(t.phrases[s.phrases]||[]).some(row=>row.id===id)).id,noteKey='phrase:'+id+':'+authored.input.key,selector='[data-phrase-card="'+id+'"]';
  const option=authored.input.options?.[0],selected={local:option?.value||'QA ingredient',english:option?.english||'shrimp'},manual={local:'QA manual ingredient',english:'shrimp (manual QA)'};
  phraseCase={id,scene,noteKey,selector,selected,manual};await activate('#travel-reference-body',scene,'local');
  const card=p.locator('#travel-reference-body '+selector);await openFields(card);
  for(const scope of ['#language-content','#travel-reference-body'])for(const language of languages){
   const field=p.locator(scope+' '+selector+' [data-phrase-input='+language+']');assert.equal(await field.getAttribute('data-note'),noteKey+(language==='english'?':english':''),'Each language must retain its own stable notes key');
   const label=await field.evaluate(el=>({names:[...el.labels].map(x=>x.textContent.trim()),targets:[...el.labels].every(x=>x.control===el)}));assert.equal(label.names.length,1);assert(label.targets&&label.names[0],'Each phrase textbox needs its own visible, correctly bound label');
   assert.equal(await p.locator(scope+' '+selector).getByRole('textbox',{name:label.names[0],exact:true,includeHidden:true}).count(),1);
  }
  for(const language of languages){
   await activate('#travel-reference-body',scene,language);await openFields(card);const input=card.locator('[data-phrase-input='+language+']');await input.fill('');await card.locator('.phrase').click();assert.equal(await p.locator('#phrase-dialog').evaluate(e=>e.open),false,'Incomplete '+language+' allergy card must not be displayed');
   await input.fill('   ');await card.locator('.phrase').click();assert.equal(await p.locator('#phrase-dialog').evaluate(e=>e.open),false,'Whitespace is not a completed '+language+' ingredient');
  }
  await activate('#travel-reference-body',scene,'local');await openFields(card);
  if(option)await card.locator('[data-phrase-choice]').selectOption(option.value);else{await card.locator('[data-phrase-input=local]').fill(selected.local);if(!englishOnly){await activate('#travel-reference-body',scene,'english');await card.locator('[data-phrase-input=english]').fill(selected.english)}}
  for(const scope of ['#language-content','#travel-reference-body'])for(const language of languages)assert.equal(await p.locator(scope+' '+selector+' [data-phrase-input='+language+']').inputValue(),selected[language],'Reference choice must synchronise both languages to main text');
  // A follow-up sentence must carry the same ingredient when opened independently.
  for(const followup of phrases.filter(row=>row.subjectFrom===id)){
   const followCard=p.locator('#travel-reference-body [data-phrase-card="'+followup.id+'"]'),followScene=scenes.find(s=>(t.phrases[s.phrases]||[]).some(row=>row.id===followup.id)).id;
   for(const language of languages){
    const field=followCard.locator('[data-phrase-input='+language+']');assert.equal(await field.getAttribute('data-note'),noteKey+(language==='english'?':english':''));assert.equal(await field.inputValue(),selected[language]);
    await activate('#travel-reference-body',followScene,language);await followCard.locator('.phrase').click();assert.equal(await p.locator('.phrase-subject').innerText(),selected[language],'Standalone follow-up must name its ingredient');
    assert.equal(await p.locator('#phrase-big h2').innerText(),followup[language==='english'?'english':'local']);await p.locator('#phrase-dialog [data-close]').click();
   }
  }
  for(const language of languages){
   const fieldKey=noteKey+(language==='english'?':english':'');assert.equal(await p.evaluate(({key,fieldKey})=>JSON.parse(localStorage.getItem(key)).notes[fieldKey],{key,fieldKey}),selected[language]);
   await activate('#travel-reference-body',scene,language);await card.locator('.phrase').click();assert.equal(await p.locator('.phrase-subject').innerText(),selected[language]);
   assert.equal(await p.locator('#phrase-big h2').innerText(),await card.locator('.phrase').getAttribute(language==='english'?'data-en':'data-jp'),'Large display must use the selected language');
   assert(await p.locator('.phrase-subject').evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=30));assert(await p.locator('#phrase-big h2').evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=28));
   for(const width of [320,390,768,1440]){await p.setViewportSize({width,height:width===1440?1000:844});assert(await p.locator('#phrase-dialog').evaluate(e=>e.scrollWidth<=e.clientWidth+1),'Large phrase overflow '+width);await p.waitForTimeout(650);await p.screenshot({path:path.join(dir,'language-large-'+language+'-'+width+'.png')})}
   await p.locator('#phrase-dialog [data-close]').click();assert(await p.locator('#travel-reference-dialog').isVisible());
  }
 }
 for(const width of [320,390,768,1440]){await p.setViewportSize({width,height:width===1440?1000:844});for(const type of ['preparation','language','dining']){await p.locator('#travel-reference-dialog .travel-reference-nav [data-reference='+type+']').click();assert(await p.locator('#travel-reference-body').evaluate(e=>e.scrollWidth<=e.clientWidth+1),'overflow '+type+width);await p.waitForTimeout(650);await p.screenshot({path:path.join(dir,type+'-'+width+'.png')})}}
 await p.locator('#travel-reference-dialog [data-close]').click();await p.locator('#pocket-dialog [data-close]').click();
 const exportBackup=async()=>{const download=p.waitForEvent('download');await p.locator('#export-data').click();return JSON.parse(fs.readFileSync(await (await download).path()))};
 const payload=await exportBackup();assert(payload.state.checks.includes(first));if(extra)assert(payload.state.checks.includes(extra));
 await p.reload();let saved=await p.evaluate(key=>JSON.parse(localStorage.getItem(key)),key);assert.equal(saved.notes.qaReference,'keep my notes');assert(saved.checks.includes(first));if(extra)assert(saved.checks.includes(extra));
 if(phraseCase){
  const {scene,selector,noteKey,selected,manual}=phraseCase,mainCard=()=>p.locator('#language-content '+selector),refCard=()=>p.locator('#travel-reference-body '+selector);
  const openLanguage=async language=>{await p.locator('#pocket-open').click();await p.locator('#pocket-dialog [data-reference=language]').click();await activate('#travel-reference-body',scene,language);await openFields(refCard())};
  const closeReference=async()=>{await p.locator('#travel-reference-dialog [data-close]').click();await p.locator('#pocket-dialog [data-close]').click()};
  const assertStored=async values=>{for(const language of languages){const fieldKey=noteKey+(language==='english'?':english':'');assert.equal(await p.evaluate(({key,fieldKey})=>JSON.parse(localStorage.getItem(key)).notes[fieldKey],{key,fieldKey}),values[language]);assert.equal(await mainCard().locator('[data-phrase-input='+language+']').inputValue(),values[language])}};
  const assertReference=async values=>{await openLanguage('local');for(const language of languages)assert.equal(await refCard().locator('[data-phrase-input='+language+']').inputValue(),values[language],'New reference clone must restore both saved ingredients');assert.equal(await refCard().locator('[data-phrase-choice]').inputValue(),values.local===selected.local?selected.local:'');await closeReference()};
  for(const language of languages)assert.equal(payload.state.notes[noteKey+(language==='english'?':english':'')],selected[language]);await assertStored(selected);await assertReference(selected);
  // Edit both fields on the main surface, then open a fresh drawer to test the reverse direction.
  for(const language of languages){await activate('#language-content',scene,language);await openFields(mainCard());await mainCard().locator('[data-phrase-input='+language+']').fill(manual[language])}
  await assertStored(manual);await assertReference(manual);const manualBackup=await exportBackup();for(const language of languages)assert.equal(manualBackup.state.notes[noteKey+(language==='english'?':english':'')],manual[language]);await p.reload();await assertStored(manual);await assertReference(manual);
  // Restore actual exported files using the normal importer, never a synthetic localStorage restore.
  for(const [name,backup,values] of [['selected',payload,selected],['manual',manualBackup,manual]]){
   for(const language of languages){await activate('#language-content',scene,language);await openFields(mainCard());await mainCard().locator('[data-phrase-input='+language+']').fill('QA changed before import')}
   await p.locator('#import-data').setInputFiles({name:'reader-reference-'+name+'.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(backup))});
   await p.waitForFunction(({key,noteKey,values,englishOnly})=>{const notes=JSON.parse(localStorage.getItem(key)).notes;return notes[noteKey]===values.local&&(englishOnly||notes[noteKey+':english']===values.english)},{key,noteKey,values,englishOnly});
   await assertStored(values);await assertReference(values);await p.reload();await assertStored(values);await assertReference(values);
   const restored=await p.evaluate(key=>JSON.parse(localStorage.getItem(key)),key);assert.equal(restored.notes.qaReference,'keep my notes');assert(restored.checks.includes(first));if(extra)assert(restored.checks.includes(extra));
  }
  report.checks.push('Local and English allergy fields have separate stable keys and labels; required/whitespace guards, option mapping, both sync directions, large display, real backup import and reload');
 }
 assert.deepEqual(report.errors,[]);report.result='pass';report.checks.push('Stable legacy/new checklist IDs, shared counts and retained user notes','All authored phrases retained; main/reference language display, 320/390/768/1440 layouts and large cards');console.log('PASS shared dining, preparation, bilingual language and travel reference state');
}catch(e){report.result='fail';report.failure=e.stack;throw e}finally{fs.writeFileSync(path.join(dir,'report.json'),JSON.stringify(report,null,2));await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
