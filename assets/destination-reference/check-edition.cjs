// Functional DOM tests; actual desktop/mobile screenshots are checked separately.
const fs=require('fs'),path=require('path'),assert=require('assert');
const R=path.resolve(process.argv[2]||__dirname);
function inputError(message) {
  console.error(message+'\nUsage: node check-edition.cjs <workbench-directory>');
  process.exit(1);
}
if(!fs.existsSync(R))inputError('Workbench directory does not exist: '+R);
if(!fs.statSync(R).isDirectory())inputError('Expected a workbench directory, received a file: '+R+'. Pass its containing workbench directory.');
if(!fs.existsSync(path.join(R,'index.html')))inputError('Missing index.html in '+R+'. Run python -X utf8 build.py in that workbench, then rerun this check.');
function dependency(name) {
  let entry;
  try {
    entry=process.env.JOURNAL_CHECK_MODULES
      ? require.resolve(path.join(path.resolve(process.env.JOURNAL_CHECK_MODULES),name))
      : require.resolve(name,{paths:[R,__dirname]});
  } catch(error) {
    throw new Error('DOM QA requires '+name+'. Run npm install in '+R+' or set JOURNAL_CHECK_MODULES to an existing node_modules directory containing jsdom, fake-indexeddb and css-tree.'+(process.env.JOURNAL_CHECK_MODULES?' Supplied directory: '+path.resolve(process.env.JOURNAL_CHECK_MODULES):''),{cause:error});
  }
  return require(entry);
}
const {JSDOM,VirtualConsole}=dependency('jsdom'),{indexedDB}=dependency('fake-indexeddb'),css=dependency('css-tree');
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const html=fs.readFileSync(path.join(R,'index.html'),'utf8'),dom=new JSDOM(html,{url:'https://edition.test',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window,d=w.document;
w.indexedDB=indexedDB;w.confirm=()=>true;w.matchMedia=()=>({matches:false,addEventListener(){}});w.IntersectionObserver=class{observe(){}disconnect(){}};w.Element.prototype.animate=()=>({finished:Promise.resolve(),cancel(){}});w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLElement.prototype.scrollTo=function(){};w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'))};w.URL.createObjectURL=()=> 'blob:test';w.URL.revokeObjectURL=()=>{};
for(const f of ['map-layout.js','map-ui.js','schedule.js','ledger-model.js','member-avatars.js','ledger-demo.js','ledger-ui.js','travel-alternatives.js','app.js','motion.js','art.js'])w.eval(fs.readFileSync(path.join(R,f),'utf8'));
const G=JSON.parse(d.querySelector('#guide-data').textContent),click=s=>{const n=d.querySelector(s);assert(n,s);n.click();return n},input=(s,v)=>{const n=d.querySelector(s);n.value=v;n.dispatchEvent(new w.Event('input',{bubbles:true}))};
(async()=>{
await new Promise(r=>setTimeout(r,80));
assert.equal(d.querySelectorAll('.chapter').length,10);assert.equal(d.querySelectorAll('.contents-grid .toc-entry').length,10);assert.equal(d.querySelectorAll('.route-essay').length,G.areas.length);
const chapterIds=[...d.querySelectorAll('.chapter')].map(n=>n.id);
for(const selector of ['.contents-grid .toc-entry','.drawer-nav .toc-entry'])assert.deepEqual([...d.querySelectorAll(selector)].map(a=>a.hash.slice(1)),chapterIds,'Contents must follow actual chapter order');
for(let i=0;i<G.days.length;i++){
 click('#day-tabs [data-day="'+i+'"]');assert.equal(d.querySelectorAll('.timeline-item').length,G.days[i].stops.length);assert(d.querySelector('.day-title').textContent===G.days[i].title);
 const plan=w.TravelSchedule.plan(G.days[i]);for(let j=1;j<plan.length;j++)assert(plan[j].start>=plan[j-1].end+plan[j].transfer.minutes);
 click('#pocket-open');assert(d.querySelector('#pocket-dialog').open);assert.equal(d.querySelectorAll('.pocket-stop').length,G.days[i].stops.length);d.querySelector('#pocket-dialog').close();
 click('[data-overview-day="'+i+'"]');assert.equal(d.querySelectorAll('.journey-map-sheet polyline').length,1);
}
assert.equal(d.querySelectorAll('[data-open-editor],[data-reorder],[data-remove-stop],#restore-day').length,0);
const allIds=new Set();for(let i=1;i<=Math.ceil(G.places.length/6);i++){click('[data-directory-page="'+i+'"]');d.querySelectorAll('[data-directory-id]').forEach(n=>allIds.add(n.dataset.directoryId))}assert.equal(allIds.size,G.places.length);
click('[data-directory-page="1"]');const first=G.places[0].id;click('[data-save="'+first+'"]');click('#saved-filter');assert.equal(d.querySelectorAll('.address-card').length,1);click('#saved-filter');
input('#place-search','绝不应存在的地点');assert(d.querySelector('.directory-empty'));click('[data-directory-reset]');
for(const tool of ['ledger','photos','files']){click('[data-tool="'+tool+'"]');assert(d.querySelector('#'+tool+'-dialog').open);d.querySelector('#'+tool+'-dialog').close()}
click('[data-tool="ledger"]');assert(d.querySelector('#ledger-totals').textContent.includes(G.edition.currency));
input('#expense-form [name="title"]','测试午餐');input('#expense-form [name="amount"]','100001');d.querySelector('#expense-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));assert(d.querySelector('#expense-list').textContent.includes('100,001'));
d.querySelector('#ledger-dialog').close();input('[data-note="journal"]','测试笔记');const state=JSON.parse(w.localStorage.getItem('travel-magazine-v4-'+G.edition.slug));assert.equal(state.notes.journal,'测试笔记');assert.equal(state.expenses.length,1);
if(d.querySelector('#notes-dialog')){
 click('[data-tool="notes"]');assert(d.querySelector('#notes-dialog').open);
 assert.equal(d.querySelector('#travel-journal').value,'测试笔记');
 input('#travel-journal','全程记录\n第二行');assert.equal(d.querySelector('#journal-note textarea').value,'全程记录\n第二行');
 click('#notes-dialog [data-day="0"]');input('#travel-day-note','第一天集合点');
 click('#notes-dialog [data-day="1"]');assert.equal(d.querySelector('#travel-day-note').value,'');assert.equal(d.querySelector('#travel-journal').value,'全程记录\n第二行');input('#travel-day-note','第二天预约');
 click('#notes-dialog [data-day="0"]');assert.equal(d.querySelector('#travel-day-note').value,'第一天集合点');
 click('#notes-dialog [data-open-pocket]');assert(!d.querySelector('#notes-dialog').open);assert.equal(d.querySelector('#pocket-dialog [data-day-note]').value,'第一天集合点');
 input('#pocket-dialog [data-day-note]','更新集合点');click('#pocket-dialog [data-tool="notes"]');assert.equal(d.querySelector('#travel-day-note').value,'更新集合点');
 click('#notes-dialog [data-tool="files"]');click('#files-dialog [data-tool="notes"]');assert.equal(d.querySelector('#travel-day-note').value,'更新集合点');
 d.querySelector('#notes-dialog').close();input('#journal-note textarea','从杂志修改');click('[data-tool="notes"]');assert.equal(d.querySelector('#travel-journal').value,'从杂志修改');
 const saved=JSON.parse(w.localStorage.getItem('travel-magazine-v4-'+G.edition.slug));assert.equal(saved.notes.journal,'从杂志修改');assert.equal(saved.notes[G.days[0].id],'更新集合点');assert.equal(saved.notes[G.days[1].id],'第二天预约');assert.equal(saved.expenses.length,1);
 d.querySelector('#notes-dialog').close();
 console.log('PASS shared notes: two-way sync, separate daily notes, date/tool switching, persisted multiline values; existing ledger preserved.');
}
click('[data-check="c0"]');assert(d.querySelector('#check-count').textContent.includes('1'));
click('.phrase');assert(d.querySelector('#phrase-dialog').open);d.querySelector('#phrase-dialog').close();
for(const n of d.querySelectorAll('a[href^="#"]'))if(n.hash)assert(d.getElementById(n.hash.slice(1)),'missing anchor '+n.hash);
for(const f of fs.readdirSync(R).filter(f=>f.endsWith('.css')))css.parse(fs.readFileSync(path.join(R,f),'utf8'));
assert.equal(errors.length,0,errors.join('\n'));
console.log('PASS',G.edition.city,':',G.days.length,'days; 10 chapters;',allIds.size,'places; maps, travel mode, search, favorites, currency, ledger, notes, checklist, language; CSS parsed.');await new Promise(r=>setTimeout(r,400));await new Promise(r=>setTimeout(r,400));w.TravelMapLayout?.dispose();w.close();
})().catch(e=>{console.error(e);w.TravelMapLayout?.dispose();w.close();process.exitCode=1});
