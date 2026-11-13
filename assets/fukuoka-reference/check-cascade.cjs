// Static cascade regression. Evaluates matching selectors, specificity and width media
// queries in source order. Does NOT lay out boxes, draw text, or replace browser QA.
const fs=require('fs'),path=require('path'),assert=require('assert');
const deps=process.env.JOURNAL_CHECK_MODULES||path.join(__dirname,'node_modules');
const {JSDOM}=require(path.join(deps,'jsdom')),css=require(path.join(deps,'css-tree'));
const dom=new JSDOM(fs.readFileSync(__dirname+'/index.html','utf8'));
const d=dom.window.document;
const styles=[...d.querySelectorAll('link[rel=stylesheet]')].map(el=>el.getAttribute('href').split('?')[0]);
const trees=styles.map(file=>({file,tree:css.parse(fs.readFileSync(path.join(__dirname,file),'utf8'))}));
const compare=(a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2];
function specificity(selector){
 const score=[0,0,0];
 const add=s=>s.forEach((n,i)=>score[i]+=n);
 selector.children.forEach(node=>{
  if(node.type==='IdSelector')score[0]++;
  else if(node.type==='ClassSelector'||node.type==='AttributeSelector')score[1]++;
  else if(node.type==='TypeSelector'&&node.name!=='*'||node.type==='PseudoElementSelector')score[2]++;
  else if(node.type==='PseudoClassSelector'){
   if(node.name==='where')return;
   if(['is','not','has'].includes(node.name)){
    let best=[0,0,0];
    node.children?.forEach(list=>list.children?.forEach(s=>{const value=specificity(s);if(compare(value,best)>0)best=value}));add(best);
   }else score[1]++;
  }
 });return score;
}
function mediaMatches(query,width,reduced){
 return query.split(',').some(branch=>{
  if(/\bprint\b/.test(branch))return false;
  for(const m of branch.matchAll(/\(([^)]+)\)/g)){
   const [name,value]=m[1].split(':').map(s=>s.trim());
   if(name==='min-width'&&width<parseFloat(value))return false;
   else if(name==='max-width'&&width>parseFloat(value))return false;
   else if(name==='prefers-reduced-motion'&&(value==='reduce')!==reduced)return false;
   else if(!['min-width','max-width','prefers-reduced-motion'].includes(name))return false;
  }return true;
 });
}
function rulesAt(width,reduced=false){
 const rules=[];
 function walk(children,file){children.forEach(node=>{
  if(node.type==='Atrule'){
   if(node.name==='media'&&mediaMatches(css.generate(node.prelude),width,reduced))walk(node.block.children,file);
   return;
  }
  if(node.type!=='Rule'||node.prelude?.type!=='SelectorList')return;
  node.prelude.children.forEach(selector=>{
   const text=css.generate(selector),declarations=[];
   node.block.children.forEach(dec=>{if(dec.type==='Declaration')declarations.push({property:dec.property,value:css.generate(dec.value),important:!!dec.important})});
   rules.push({selector:text,specificity:specificity(selector),declarations,file});
  });
 })}
 trees.forEach(({tree,file})=>walk(tree.children,file));return rules;
}
function winner(el,property,rules){
 let result=null;
 for(const rule of rules){
  let matches=false;try{matches=el.matches(rule.selector)}catch{}if(!matches)continue;
  for(const declaration of rule.declarations){
   if(declaration.property!==property)continue;
   const candidate={...declaration,...rule};
   if(!result||Number(candidate.important)>Number(result.important)||(candidate.important===result.important&&compare(candidate.specificity,result.specificity)>=0))result=candidate;
  }
 }return result;
}
const toc=d.querySelector('.journal-contents'),intro=toc.querySelector('.contents-intro'),heading=toc.querySelector('h2>span'),nav=toc.querySelector('.contents-grid');
const widths=[320,375,390,414,600,601,700,701,768,850,851,1024,1280,1600];
for(const width of widths){
 const rules=rulesAt(width),value=(el,prop)=>winner(el,prop,rules)?.value;
 assert.equal(value(toc,'display'),'grid',width+' contents layout');
 assert.equal(value(intro,'display'),width<=600||width>850?'block':'grid',width+' intro must never inherit old flex rule');
 assert.equal(value(intro,'min-width'),'0');
 assert.equal(value(heading,'white-space'),'nowrap',width+' title wraps by phrase, never by character');
 assert.equal(value(heading,'display'),width<=850?'inline-block':'block');
 assert.equal(value(nav,'grid-template-columns'),width<=600?'1fr':width<=850?'1fr 1fr':'repeat(2,minmax(0,1fr))');
 assert.equal(value(d.querySelector('.topbar .masthead>span'),'display'),'inline',width+' masthead text must survive legacy mobile span hiding');
 assert.equal(value(d.querySelector('#place-dialog'),'--place-arrival'),width<=600?'place-sheet-arrive':undefined);
 assert.equal(value(d.querySelector('#place-dialog'),'height'),width<=600?'94dvh':'100dvh');
 // A narrow page should never retain the desktop sidebar/table widths.
 assert.equal(value(d.querySelector('#place-results'),'grid-template-columns'),width<=600?'1fr':'repeat(2,minmax(0,1fr))');
 // Dynamic timeline uses the same selectors as the app, with no browser involved.
 const timeline=d.createElement('div');timeline.className='timeline';
 assert.equal(value(timeline,'--timeline-axis'),width<=370?'58px':width<=700?'65px':'92px');
 // Editorial changes must collapse both the opening spread and every district.
 assert.equal(value(d.querySelector('.fashion-opening-note'),'grid-template-columns'),width<=600?'minmax(0,1fr)':'minmax(0,.9fr) minmax(0,1fr)');
 assert.equal(value(d.querySelector('.section-head'),'grid-template-columns'),'minmax(0,1fr)');
 assert.equal(value(d.querySelector('.fashion-night-layout'),'display'),'block');
 assert.equal(value(d.querySelector('.fashion-afterword-copy'),'grid-template-columns'),width<=850?'1fr':'minmax(0,1.25fr) minmax(0,.75fr)');
  // The bay/river bleed; the lake and tower retain a bounded, landmark-safe crop.
  const lake=d.querySelector('#area-ohori .district-spread>figure');
  assert.equal(value(lake,'width'),'100%',width+' bounded lake photograph');
  assert.equal(value(lake,'position'),'static');
  assert.equal(value(lake.querySelector('img'),'object-position'),width<=370?'76%center':width<=600?'59%center':'50% 43%');
  assert.equal(value(lake.querySelector('img'),'transform'),'none','The bridge photo must not inherit the previous 2× mobile lake crop');
  assert.equal(value(d.querySelector('#area-momochi .district-spread>figure'),'width'),'100%',width+' bounded tower photograph');
  // The closing photo and lead previously occupied the same cell, hiding the text.
  const closing=d.querySelector('#area-dazaifu .district-spread');
  assert.equal(value(closing.querySelector('.district-lead'),'grid-column'),'1',width+' Dazaifu lead remains visible');
  assert.equal(value(closing.querySelector('figure'),'grid-column'),width<=850?'1':'2',width+' Dazaifu photograph column');
  assert.equal(value(closing.querySelector('.district-lead'),'grid-row'),width<=850?'2':'1',width+' Dazaifu reading order');
  for(const bleed of d.querySelectorAll('.fashion-bleed,.spread-river .district-spread>figure')){
  assert.equal(value(bleed,'width'),'100vw',width+' edge-to-edge photograph');
  assert.equal(value(bleed,'left'),'50%');
  assert.equal(value(bleed,'margin-inline-start'),'-50vw');
   const bay=bleed.matches('.fashion-bleed');
   assert.equal(value(bleed.querySelector('img'),'height'),bay?(width<=600?'440px':'clamp(440px,68svh,760px)'):(width<=600?'430px':'clamp(440px,65svh,740px)'));
 }
 if(width<=600){
  for(const spread of d.querySelectorAll('.district-spread')){
   const pair=spread.closest('.spread-pair');
   assert.equal(value(spread,'grid-template-columns'),'minmax(0,1fr)',width+' district mobile grid');
   assert.equal(value(spread.querySelector('.district-lead'),'grid-row'),pair?'3':'2',width+' district reading order');
   assert.equal(value(spread.querySelector('.district-lead'),'display'),'block',width+' district readable prose');
  }
 }
}
// Negative control: the exact old selector responsible for the screenshot must win
// if we put the legacy hook back, showing this test exercises CSS specificity.
toc.className='contents contents-edition wrap';
const broken=winner(intro,'display',rulesAt(1600));
assert.equal(broken.value,'flex');assert.equal(broken.selector,'.contents>div:first-child');
toc.className='journal-contents wrap';
console.log('PASS: '+styles.length+' stylesheet cascade at 14 widths (320–1600 px), Dazaifu non-overlapping cells, full-bleed photos, contents, mobile editorial spreads / all districts, mobile sheet, timeline alignment and directory columns; old flex conflict negative control. Static check, not a rendering test.');
dom.window.close();
