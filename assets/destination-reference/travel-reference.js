/* A shared reference drawer clones authored content, never a second copy of the facts. */
(()=>{'use strict';
 let context=null,current='dining';
 const $=s=>document.querySelector(s),all=s=>[...document.querySelectorAll(s)];
 const titles={dining:'吃什么',preparation:'准备清单',language:'随身语言'};
 const languageState={scene:null,view:'phrases',mode:'local'};
 function syncLanguage(){
  all('[data-language-workbench]').forEach(root=>{
   const scenes=[...root.querySelectorAll('[data-language-scene]')];
   const scene=scenes.some(b=>b.dataset.languageScene===languageState.scene)?languageState.scene:scenes[0]?.dataset.languageScene;
   const mode=root.querySelector('[data-language-mode=english]')?languageState.mode:'local';root.dataset.language=mode;
   root.querySelectorAll('[data-language-text]').forEach(e=>e.hidden=e.dataset.languageText!==mode);
   root.querySelectorAll('[data-language-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.languageMode===mode)));
   scenes.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.languageScene===scene)));
   root.querySelectorAll('[data-language-panel]').forEach(panel=>{
    panel.hidden=panel.dataset.languagePanel!==scene;
    const views=[...panel.querySelectorAll('[data-language-view]')];
    const view=views.some(b=>b.dataset.languageView===languageState.view)?languageState.view:views[0]?.dataset.languageView;
    views.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.languageView===view)));
    panel.querySelectorAll('[data-language-pane]').forEach(e=>e.hidden=e.dataset.languagePane!==view);
   });
  });
 }
 function clone(source){
  const node=source.cloneNode(true);
  for(const element of [node,...node.querySelectorAll('[id]')])element.removeAttribute('id');
  return node;
 }
 function render(type,restaurant,showAll=false){
  current=type;
  const dialog=$('#travel-reference-dialog'),body=$('#travel-reference-body');body.replaceChildren();
  $('#travel-reference-title').textContent=titles[type];
  dialog.querySelectorAll('[data-reference]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.reference===type)));
  if(type==='dining'){
   const source=$('#restaurant-guide');if(!source)return;
   const guide=clone(source),ids=context.d.dining||context.d.stops.map(s=>s[1]);
   const intro=document.createElement('p');intro.className='reference-scope';intro.textContent=showAll?'全程餐厅候选':'第 '+context.d.id.slice(1)+' 天 · '+context.d.area+' · 按营业和时间选择';body.append(intro);
   guide.querySelectorAll('.restaurant-pick').forEach(card=>{
    const id=card.dataset.restaurantId;if(!showAll&&!ids.includes(id)){card.remove();return}card.open=id===restaurant;
   });
   guide.querySelectorAll('.restaurant-group').forEach(group=>{const n=group.querySelectorAll('.restaurant-pick').length;if(!n)group.remove();else {const count=group.querySelector('header h3 small');if(count)count.textContent=n+' 家'}});
   if(!guide.querySelector('.restaurant-pick')){const empty=document.createElement('p');empty.textContent='当天未指定餐厅，可查看全程候选，按实际位置与营业选择。';body.append(empty)}
   if(!showAll)guide.querySelectorAll('.restaurant-group>header>p:not(.kicker)').forEach(e=>e.remove());
   body.append(guide);
   const toggle=document.createElement('button');toggle.className='reference-all';toggle.dataset.referenceAll=String(!showAll);toggle.textContent=showAll?'只看当天候选':'查看全部餐厅';body.append(toggle);
  }else{
   const source=$(type==='preparation'?'#preparation-content':'#language-content');if(source)body.append(clone(source));
  }
  context.syncInputs();context.openDialog('#travel-reference-dialog');body.scrollTop=0;
  if(restaurant)requestAnimationFrame(()=>{const card=[...body.querySelectorAll('[data-restaurant-id]')].find(e=>e.dataset.restaurantId===restaurant);card?.scrollIntoView({block:'start',behavior:'instant'})});
 }
 window.TravelReference={
  syncFields(){all('[data-phrase-input]').forEach(shareInput);syncLanguage()},
  open(type,ctx,restaurant){context=ctx;render(type,restaurant)},
  quicklinks(){return '<div class="pocket-quicklinks"><button data-reference="language">随身语言 ↗</button></div>'},
  dining(d,{P,esc}){
   const route=new Set(d.stops.map(s=>s[1])),ids=(d.dining||[...route]).filter(id=>P[id]&&$('#eat-'+id));
   if(!ids.length)return '';
   return '<details class="pocket-reading pocket-dining"><summary><span>今天吃什么</span><small>'+ids.length+' 家候选 ＋</small></summary><div class="dining-shortlist">'+ids.map(id=>{const summary=$('#eat-'+id+' .restaurant-summary-copy>span')?.textContent||P[id].area;return '<button data-reference="dining" data-restaurant="'+esc(id)+'"><strong>'+esc(P[id].name)+'</strong><span>'+esc(summary)+'</span><small>'+(route.has(id)?'行程中的用餐':'可替换候选')+' · 点单与营业 ↗</small></button>'}).join('')+'</div><button class="reference-all" data-reference="dining">查看当天用餐详情 ↗</button></details>';
  },
  showPhrase(button,{lang,esc,openDialog}){
   const mode=button.closest('[data-language-workbench]')?.dataset.language||'local',card=button.closest('.phrase-card');
   const input=card?.querySelector('[data-phrase-input='+mode+']');
   if(input){input.value=input.value.trim();if(!input.checkValidity()){card.querySelector('.phrase-fields').open=true;input.reportValidity();return}}
   const code=mode==='english'?'en':lang,text=mode==='english'?button.dataset.en:button.dataset.jp;
   if(!text)return;
   $('#phrase-big').innerHTML=(input?.value?'<p class="phrase-subject" lang="'+esc(code)+'">'+esc(input.value)+'</p>':'')+'<h2 lang="'+esc(code)+'">'+esc(text)+'</h2><p>'+esc(button.dataset.zh)+'</p>'+(mode==='local'&&button.dataset.rom?'<details class="phrase-help"><summary>查看读音</summary><p lang="en">'+esc(button.dataset.rom)+'</p></details>':'');
   openDialog('#phrase-dialog');
  }
 };
 document.addEventListener('click',e=>{
  const button=e.target.closest('[data-reference-all]');if(button&&context)render('dining',null,button.dataset.referenceAll==='true');
  const control=e.target.closest('[data-language-mode],[data-language-scene],[data-language-view]');if(!control)return;
  if(control.dataset.languageMode)languageState.mode=control.dataset.languageMode;
  if(control.dataset.languageScene)languageState.scene=control.dataset.languageScene;
  if(control.dataset.languageView)languageState.view=control.dataset.languageView;
  syncLanguage();
 });
 function shareInput(input){
  all('[data-phrase-input]').filter(e=>e.dataset.note===input.dataset.note).forEach(target=>{
   if(target!==input)target.value=input.value;
   const card=target.closest('.phrase-card'),select=card.querySelector('[data-phrase-choice]'),local=card.querySelector('[data-phrase-input=local]');
   if(select&&local)select.value=[...select.options].some(o=>o.value===local.value)?local.value:'';
  });
 }
 document.addEventListener('change',e=>{if(e.target.hasAttribute('data-phrase-choice')){
  const card=e.target.closest('.phrase-card'),option=e.target.selectedOptions[0],local=card.querySelector('[data-phrase-input=local]'),english=card.querySelector('[data-phrase-input=english]');
  const value=option?.value||'',translation=option?.dataset.english||'';
  local.value=value;local.dispatchEvent(new Event('input',{bubbles:true}));
  if(english){english.value=translation;english.dispatchEvent(new Event('input',{bubbles:true}))}
 }});
 document.addEventListener('input',e=>{if(e.target.hasAttribute('data-phrase-input')){
  const input=e.target;shareInput(input);
  if(input.dataset.phraseInput==='local'){
   const english=input.closest('.phrase-card').querySelector('[data-phrase-input=english]');
   if(english?.value){english.value='';english.dispatchEvent(new Event('input',{bubbles:true}))}
  }
 }});
})();
