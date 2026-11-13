// DOM emulation only: does not launch a browser or claim layout/visual coverage.
const fs=require('fs'),path=require('path'),assert=require('assert');
const deps=process.env.JOURNAL_CHECK_MODULES||path.join(__dirname,'node_modules');
const {JSDOM,VirtualConsole}=require(path.join(deps,'jsdom'));
const {indexedDB}=require(path.join(deps,'fake-indexeddb'));
const css=require(path.join(deps,'css-tree'));
const html=fs.readFileSync(__dirname+'/index.html','utf8'),errors=[];
const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e));
const dom=new JSDOM(html,{url:'https://fukuoka.test/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
const w=dom.window,d=w.document;
w.indexedDB=indexedDB;w.confirm=()=>true;
const media=new Map(),observers=[],animations=[];
w.matchMedia=q=>{if(!media.has(q))media.set(q,{matches:q.includes('min-width'),listeners:[],addEventListener(_,fn){this.listeners.push(fn)}});return media.get(q)};
w.IntersectionObserver=class{constructor(fn){this.fn=fn;this.nodes=[];observers.push(this)}observe(node){this.nodes.push(node)}unobserve(node){this.nodes=this.nodes.filter(n=>n!==node)}disconnect(){this.nodes=[]}};
w.Element.prototype.animate=function(frames,options){const a={node:this,frames,options,finished:Promise.resolve(),cancelled:false,cancel(){this.cancelled=true},pause(){},play(){}};animations.push(a);return a};
w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLElement.prototype.scrollTo=function(){};
w.HTMLDialogElement.prototype.showModal=function(){this.open=true};
w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'))};
w.URL.createObjectURL=()=> 'blob:test';w.URL.revokeObjectURL=()=>{};
const G=JSON.parse(d.querySelector('#guide-data').textContent),key='fukuoka-private-journal-v4-20261106';
const legacy={version:1,day:0,modes:{d1:'rain'},custom:{d1:['airport']},saved:['hakata'],checks:['c0'],notes:{hotel:'保留酒店笔记','start:d1':'23:00'},members:['我'],expenses:[],budget:60000};
w.localStorage.setItem(key,JSON.stringify(legacy));
for(const f of ['map-ui.js','schedule.js','ledger-model.js','app.js','motion.js','art.js'])w.eval(fs.readFileSync(__dirname+'/'+f,'utf8'));
const click=selector=>{const el=d.querySelector(selector);assert(el,selector);el.click();return el};
const tick=()=>new Promise(r=>setTimeout(r,30));
(async()=>{
 await tick();
 assert.equal(d.querySelectorAll('.chapter').length,10);
 assert.equal(d.querySelectorAll('.contents-grid .toc-column').length,2);
 assert.equal(d.querySelectorAll('.contents-grid .toc-entry').length,10);
 assert(d.querySelector('.journal-contents'));
 assert.equal(d.querySelectorAll('.contents,.contents-edition,.chapter-rail').length,0,'Legacy layout hooks and duplicate rail must not return');
 assert.equal(d.querySelectorAll('.district-guide').length,6);
 assert.equal(d.querySelectorAll('#menu-dialog .toc-entry').length,10);
 assert.equal(d.querySelectorAll('.reading-actions [data-open-pocket]').length,0,'Only one permanent travel-mode entry');
 click('[data-open-menu]');assert(d.querySelector('#menu-dialog').open);assert.equal(d.querySelector('#menu-open').getAttribute('aria-expanded'),'true');
 click('#menu-dialog a[href="#directory"]');assert(!d.querySelector('#menu-dialog').open);assert.equal(d.querySelector('[data-open-menu]').getAttribute('aria-expanded'),'false');
 assert.equal(d.querySelectorAll('.address-card').length,6);
 assert.deepEqual([...d.querySelectorAll('.contents-grid .toc-number')].map(n=>n.textContent),Array.from({length:10},(_,i)=>String(i+1).padStart(2,'0')));
 const allIds=new Set();
 for(let page=1;page<=4;page++){click('#directory-pages [data-directory-page="'+page+'"]');d.querySelectorAll('[data-directory-id]').forEach(el=>allIds.add(el.dataset.directoryId));assert(d.querySelector('.directory-pages [aria-current="page"]').textContent===String(page))}
 assert.equal(allIds.size,20);click('#directory-pages [data-directory-page="1"]');
 click('[data-directory-area="dazaifu"]');assert.equal(d.querySelectorAll('.address-card').length,3);assert(!d.querySelector('#directory-pages button'));
 click('[data-directory-reset]');assert.equal(d.querySelectorAll('.address-card').length,6);
 w.dispatchEvent(new w.Event('beforeprint'));assert.equal(d.querySelectorAll('.address-card').length,20);w.dispatchEvent(new w.Event('afterprint'));assert.equal(d.querySelectorAll('.address-card').length,6);
 click('#saved-filter');assert.equal(d.querySelectorAll('.address-card').length,1);click('#saved-filter');
 const kind=d.querySelector('#kind-filter');kind.value='文化';kind.dispatchEvent(new w.Event('change',{bubbles:true}));assert([...d.querySelectorAll('.directory-meta')].every(n=>n.textContent.includes('文化')));click('[data-directory-reset]');
 const emptySearch=d.querySelector('#place-search');emptySearch.value='不存在的测试地点';emptySearch.dispatchEvent(new w.Event('input',{bubbles:true}));assert(d.querySelector('.directory-empty'));click('.directory-empty [data-directory-reset]');
 assert.equal(d.querySelectorAll('.tip-card').length,48);assert.equal(d.querySelectorAll('.tip-panel:not([hidden])').length,1);assert.equal(d.querySelectorAll('[data-tip-topic]').length,8);
 click('[data-tip-topic="help"]');assert(!d.querySelector('#tip-help').hidden);assert(d.querySelector('#tip-help').textContent.includes('050-3816-2787'));
 d.querySelector('[data-tip-topic="help"]').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Home',bubbles:true}));assert.equal(d.activeElement.dataset.tipTopic,'arrival');
 for(const tab of d.querySelectorAll('[data-tip-topic]')){tab.click();assert.equal(d.querySelectorAll('.tip-panel:not([hidden])').length,1);assert.equal(d.querySelector('.tip-panel:not([hidden])').id,'tip-'+tab.dataset.tipTopic)}
 assert.equal(d.querySelector('[data-note="hotel"]').value,'保留酒店笔记');
 assert(d.querySelector('[data-check="c0"]').checked);
 for(let day=0;day<4;day++){
  click('#day-tabs [data-day="'+day+'"]');
  assert.equal(d.querySelectorAll('.timeline-item').length,G.days[day].stops.length);
  const actual=[...d.querySelectorAll('.timeline-item [data-place]')].map(x=>x.dataset.place);
  assert.deepEqual(actual,G.days[day].stops.map(s=>s[1]));
  click('[data-open-pocket]');
  assert(d.querySelector('#pocket-dialog').open);
  assert.equal(d.querySelectorAll('.pocket-stop').length,actual.length);
  assert.equal(d.querySelector('.pocket-stop time').textContent.split('–')[0],d.querySelector('.stop-stamp time').textContent);
  d.querySelector('#pocket-dialog').close();
 }
 assert.equal(d.querySelectorAll('[data-open-editor],[data-reorder],[data-remove-stop],[data-add-place],.time-editor,[data-mode],#edit-day,#restore-day').length,0);
 for(const el of d.querySelectorAll('a[href^="#"]'))if(el.hash)assert(d.getElementById(el.hash.slice(1)),'missing anchor '+el.hash);
 const ids=[...d.querySelectorAll('[id]')].map(el=>el.id);assert.equal(new Set(ids).size,ids.length,'duplicate IDs');
 click('#place-results [data-place="hakata"]');assert(d.querySelector('#place-dialog').open);assert(!d.querySelector('.add-to-day'));
 click('#place-detail [data-save="hakata"]');assert(!JSON.parse(w.localStorage.getItem(key)).saved.includes('hakata'));
 click('#place-detail [data-save="hakata"]');d.querySelector('#place-dialog').close();
 const search=d.querySelector('#place-search');search.value='太宰府';search.dispatchEvent(new w.Event('input',{bubbles:true}));assert(d.querySelectorAll('.address-card').length>0&&d.querySelectorAll('.address-card').length<20);
 for(const tool of ['ledger','photos','files']){click('#travel-tools [data-tool="'+tool+'"]');await tick();assert(d.querySelector('#'+tool+'-dialog').open);d.querySelector('#'+tool+'-dialog').close()}
 const note=d.querySelector('[data-note="journal"]');note.value='这次的笔记';note.dispatchEvent(new w.Event('input',{bubbles:true}));assert.equal(JSON.parse(w.localStorage.getItem(key)).notes.journal,'这次的笔记');
 // Day and tool changes keep one shared shell, the selected day, notes and keyboard focus.
 click('[data-open-pocket]');assert.equal(d.querySelectorAll('.travel-dialog').length,4);
 assert.equal(d.querySelectorAll('#pocket-dialog .tool-context').length,1);
 click('#pocket-dialog [data-day="1"]');assert.equal(d.activeElement.dataset.day,'1');
 const dayNote=d.querySelector('[data-day-note]');dayNote.value='18:00 晚餐预约';dayNote.dispatchEvent(new w.Event('input',{bubbles:true}));
 click('#pocket-dialog [data-tool="ledger"]');assert(!d.querySelector('#pocket-dialog').open);assert(d.querySelector('#ledger-dialog').open);assert.equal(d.querySelector('#ledger-dialog').dataset.arrival,'switch');
 click('#ledger-dialog [data-day="2"]');click('#ledger-dialog [data-open-pocket]');assert.equal(d.querySelector('#pocket-dialog [aria-pressed="true"]').dataset.day,'2');
 click('#pocket-dialog [data-day="1"]');assert.equal(d.querySelector('[data-day-note]').value,'18:00 晚餐预约');
 d.querySelector('#pocket-dialog').close();assert(!d.body.classList.contains('travel-open'));
 assert.equal(d.querySelectorAll('.image-reveal-veil').length,0);assert(!animations.some(a=>a.node.classList.contains('word-ink')),'Ordinary headings do not repeat entrance animations');
 // Map drawing must retain dashed/solid semantics and remove temporary SVG masks.
 w.SVGElement.prototype.getTotalLength=function(){return 900};
 click('[data-overview-day="2"]');
 assert(d.querySelector('.route-drawing-stroke'));
 const route=d.querySelector('#journey-overview svg>polyline');assert.equal(route.getAttribute('stroke-dasharray'),'12 8');assert(route.hasAttribute('mask'));
 assert(animations.some(a=>a.frames[0].strokeDashoffset===900));await tick();assert(!route.hasAttribute('mask'));assert.equal(d.querySelectorAll('#journey-overview mask').length,0);
 click('[data-overview-day="all"]');click('[data-overview-day="1"]');await tick();assert.equal(d.querySelectorAll('#journey-overview mask').length,0);
 // A simulated viewport checks reading state, without pretending to measure layout.
 const timeline=d.querySelector('.timeline'),stops=[...timeline.querySelectorAll('.timeline-item')];
 timeline.getBoundingClientRect=()=>({top:-100,bottom:1400,height:1500});stops.forEach((s,i)=>s.getBoundingClientRect=()=>({top:-100+i*300,bottom:200+i*300,height:300}));
 w.dispatchEvent(new w.Event('scroll'));await tick();assert.equal(d.querySelectorAll('.timeline-item.is-reading').length,1);assert(stops[1].classList.contains('is-reading'));assert(Number(timeline.style.getPropertyValue('--timeline-read'))>0);
 // The lightbox expands with uniform scaling and a crop, not distorted X/Y scales.
 const source=d.querySelector('img[data-zoom]'),big=d.querySelector('#photo-big');
 source.getBoundingClientRect=()=>({left:40,top:180,width:240,height:160});big.getBoundingClientRect=()=>({left:100,top:100,width:900,height:600});
 Object.defineProperty(big,'complete',{value:true});Object.defineProperty(big,'naturalWidth',{value:1800});source.click();
 assert(d.querySelector('#photo-dialog').open);assert(animations.some(a=>a.node===big&&a.frames[0].clipPath&&a.frames[0].transform.includes('scale(')));d.querySelector('#photo-dialog').close();
 click('[data-overview-day="0"]');assert(d.querySelector('#journey-overview mask'));
 const artObserver=observers.find(o=>o.nodes.some(n=>n.matches('.art-nightfall'))),scene=d.querySelector('.art-nightfall');
 assert.equal(artObserver.nodes.length,3,'Only three signature photographs animate');
 scene.getBoundingClientRect=()=>({top:600,height:800,bottom:1400});
 const bay=d.querySelector('.art-seaside'),night=d.querySelector('.art-afterdark');
 bay.getBoundingClientRect=()=>({top:400,height:600,bottom:1000});night.getBoundingClientRect=()=>({top:600,height:800,bottom:1400});
 artObserver.fn([scene,bay,night].map(target=>({isIntersecting:true,target})));await tick();
 assert(parseFloat(scene.style.getPropertyValue('--opening-inset'))>0);assert.notEqual(bay.style.getPropertyValue('--bay-depth'),'');assert(parseFloat(night.style.getPropertyValue('--night-offset'))>0);
 scene.getBoundingClientRect=()=>({top:0,height:800,bottom:800});w.dispatchEvent(new w.Event('scroll'));await tick();assert.equal(parseFloat(scene.style.getPropertyValue('--opening-inset')),0);
 const before=animations.length;click('[data-motion-toggle]');await tick();assert.equal(scene.style.getPropertyValue('--opening-inset'),'','Motion off restores full photograph');assert.equal(bay.style.getPropertyValue('--bay-depth'),'');assert.equal(night.style.getPropertyValue('--night-offset'),'');assert.equal(d.documentElement.dataset.motion,'off');assert.equal(w.localStorage.getItem('fukuoka-motion'),'off');assert.equal(animations.length,before);
 assert.equal(d.querySelectorAll('#journey-overview mask,[mask]').length,0,'Switching motion off restores complete map strokes immediately');
 click('[data-overview-day="1"]');source.click();assert.equal(animations.length,before);d.querySelector('#photo-dialog').close();
 click('[data-motion-toggle]');const reduced=media.get('(prefers-reduced-motion: reduce)');reduced.matches=true;reduced.listeners.forEach(fn=>fn());assert.equal(d.documentElement.dataset.motion,'off');
 const parseErrors=[];for(const file of ['editorial-layout.css','reader-components.css','tokens.css','magazine.css','fashion.css','art.css','ui-polish.css'])css.parse(fs.readFileSync(__dirname+'/'+file,'utf8'),{onParseError:e=>parseErrors.push(e)});assert.equal(parseErrors.length,0);
 assert.equal(errors.length,0,errors.map(e=>e.message).join('\n'));
 console.log('PASS: DOM boot, 4 days + shared travel tools/day-note/focus sync, contents, 20 places / filters, 48 tips / keyboard navigation, three distinct scroll scenes, dashed map drawing + cleanup, timeline reading state, uniform photo expansion, motion/reduced-motion settings, CSS syntax (no real layout rendering)');
 w.close();
})().catch(e=>{console.error(e);w.close();process.exitCode=1});
