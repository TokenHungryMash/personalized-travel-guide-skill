/* Chapter-local navigation; date actions use the shared itinerary state. */
(()=>{'use strict';
 const $=s=>document.querySelector(s),all=s=>[...document.querySelectorAll(s)];
 const G=JSON.parse($('#guide-data').textContent),host=$('.reading-shortcuts'),bar=$('.reading-actions');
 if(!host||!bar)return;
 host.replaceChildren();host.classList.add('context-scroll');host.setAttribute('aria-label','当前章节小节');
 const shell=document.createElement('div');shell.className='context-shell';host.before(shell);shell.append(host);
 const more=document.createElement('button');more.className='context-more';more.type='button';more.setAttribute('aria-label','向右查看更多小节');more.textContent='›';shell.append(more);
 const reduced=()=>document.documentElement.dataset.motion==='off';
 const dock=document.createElement('nav');dock.className='mobile-day-dock';dock.hidden=true;dock.setAttribute('aria-label','行程日期，全部旅行日');
 G.days.forEach((d,i)=>{const b=document.createElement('button');b.type='button';b.dataset.day=i;b.setAttribute('aria-label','第 '+(i+1)+' 天 · '+d.area);const number=document.createElement('b'),name=document.createElement('small');number.textContent=String(i+1).padStart(2,'0');name.textContent=d.dockLabel?.trim()||(i===0?'抵达':i===G.days.length-1?'返程':d.area.split(/[·・→]/)[0].trim());b.append(number,name);dock.append(b)});
 dock.style.setProperty('--dock-days',G.days.length);
 if(G.days.length>7){dock.classList.add('is-long');dock.replaceChildren();
  const prev=document.createElement('button'),next=document.createElement('button'),label=document.createElement('label'),select=document.createElement('select');
  prev.type=next.type='button';prev.textContent='‹';next.textContent='›';prev.setAttribute('aria-label','前一天');next.setAttribute('aria-label','后一天');prev.dataset.step='-1';next.dataset.step='1';
  select.setAttribute('aria-label','选择旅行日期');G.days.forEach((d,i)=>{const o=document.createElement('option');o.value=i;o.textContent='第 '+(i+1)+' / '+G.days.length+' 天 · '+d.area;select.append(o)});
  select.addEventListener('change',()=>{$('#day-tabs [data-day="'+select.value+'"]').click();requestAnimationFrame(()=>{jump($('#day-view'));update($('#itinerary'));});});label.append(select);dock.append(prev,label,next);
 }document.body.append(dock);
 const dayStatus=document.createElement('span');dayStatus.className='mobile-day-status';bar.append(dayStatus);
 let currentKey='',items=[],lastActive='';
 const label=e=>(e?.textContent||'').replace(/\s*[＋+].*$/,'').trim();
 function anchor(el,text,id){if(!el)return null;if(!el.id)el.id=id;el.classList.add('reader-target');return {text,target:el.id};}
 function sectionItems(key){
  const c=$('#'+key),links=(selector,fn)=>all(selector).map((e,i)=>anchor(e,fn(e,i),'reader-'+key+'-'+i));
  switch(key){
   case 'itinerary':return G.days.map((d,i)=>({text:'第 '+(i+1)+' 天',short:String(i+1).padStart(2,'0'),day:i,title:'第 '+(i+1)+' 天 · '+d.area}));
   case 'neighbourhoods':return G.areas.map(a=>anchor($('#area-'+a.id),a.name));
   case 'orientation':return [anchor(c.querySelector('.city-portrait'),'城市印象','reader-city'),anchor(c.querySelector('.subheading'),'住宿分区','reader-stays'),anchor(c.querySelector('.wide-detail'),'预订记录','reader-bookings')];
   case 'food':return [anchor(c.querySelector('.edition-feature'),'当地味道','reader-food-intro'),...links('#food .restaurant-group',e=>label(e.querySelector('header h3'))),anchor(c.querySelector('.food-reading'),'菜单与小吃','reader-menu')];
   case 'culture':return [anchor(c.querySelector('.edition-feature'),'城市文化','reader-culture-intro'),anchor(c.querySelector('.editorial-table'),'参观指南','reader-culture-guide'),anchor(c.querySelector('.shortlist'),'参观地点','reader-culture-places')];
   case 'shopping':return [...links('#shopping .editorial-table article',e=>label(e.querySelector('h4'))),anchor(c.querySelector('.shortlist'),'购物地点','reader-shopping-places'),anchor(c.querySelector('.wish-label'),'愿望单','reader-wishlist')];
   case 'fieldnotes':return [...links('#fieldnotes .note-fold',e=>label(e.querySelector('summary h3'))),anchor(c.querySelector('.wish-label'),'联络卡','reader-contacts')];
   case 'prepare':return [anchor(c.querySelector('.editorial-table'),'提前预约','reader-reservations'),anchor(c.querySelector('.check-summary'),'准备清单','reader-checks'),anchor(c.querySelector('#language-content'),'语言锦囊','reader-language')];
   case 'directory':return [{text:'全部地点',action:'all'},{text:'我的收藏',action:'saved'},anchor(c.querySelector('.directory-search'),'搜索','reader-search'),anchor($('#directory-areas'),'区域筛选')];
   case 'tools':return [{text:'记账',tool:'ledger'},{text:'笔记',tool:'notes'},{text:'摄影',tool:'photos'},{text:'票据',tool:'files'},anchor($('#travel-tools'),'备份与导入')];
   default:return [anchor($('#reading-start'),'读前说明'),anchor($('.journal-contents'),'全书目录','reader-contents'),anchor($('#orientation'),'认识目的地')];
  }
 }
 const catalogs=new Map(['cover',...all('.chapter').map(c=>c.id)].map(key=>[key,sectionItems(key).filter(Boolean)]));
 function openFragment(){let id;try{id=decodeURIComponent(location.hash.slice(1));}catch{return;}const target=document.getElementById(id);if(target?.tagName==='DETAILS')target.open=true;}
 openFragment();addEventListener('hashchange',openFragment);
 const initialFragment=location.hash;let userNavigated=false;
 if(initialFragment){
  for(const type of ['wheel','touchstart','pointerdown','keydown'])addEventListener(type,()=>{userNavigated=true;},{once:true,passive:true});
  addEventListener('pageshow',e=>{if(e.persisted)return;document.fonts.ready.then(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>{
   if(userNavigated||location.hash!==initialFragment)return;let id;try{id=decodeURIComponent(initialFragment.slice(1));}catch{return;}document.getElementById(id)?.scrollIntoView({behavior:'instant',block:'start'});
  })));},{once:true});
 }
 function overflow(){const scrollable=host.scrollWidth>shell.clientWidth+3;more.hidden=!scrollable;shell.classList.toggle('has-more',scrollable);const atEnd=host.scrollWidth-host.clientWidth-host.scrollLeft<3;more.dataset.back=String(atEnd);more.textContent=atEnd?'‹':'›';more.setAttribute('aria-label',atEnd?'返回首个小节':'向右查看更多小节');}
 function reveal(el){if(!el)return;const a=el.getBoundingClientRect(),b=host.getBoundingClientRect();if(a.left<b.left||a.right>b.right)host.scrollLeft+=a.left-b.left-(b.width-a.width)/2;overflow();}
 function render(key){
  currentKey=key;items=catalogs.get(key)||catalogs.get('cover');lastActive='';host.replaceChildren();bar.dataset.context=key;
  items.forEach((item,i)=>{const e=document.createElement(item.target?'a':'button');e.dataset.contextIndex=i;
   e.textContent=item.text;e.title=item.title||item.text;
   if(item.target)e.href='#'+item.target;else e.type='button';
   if(item.day!==undefined){e.dataset.day=item.day;e.setAttribute('aria-label',item.title);const short=document.createElement('span');short.className='context-short';short.textContent=item.short;const long=document.createElement('span');long.className='context-long';long.textContent=item.text;e.replaceChildren(long,short);}
   if(item.tool)e.dataset.tool=item.tool;
   host.append(e);
  });host.scrollLeft=0;requestAnimationFrame(overflow);
 }
 function update(chapter){
  const key=chapter?.id||'cover';if(key!==currentKey)render(key);
  dock.hidden=key!=='itinerary';const day=Number($('#day-tabs [aria-pressed=true]')?.dataset.day??0);dock.querySelectorAll('button').forEach(b=>{if(b.dataset.step){const n=day+Number(b.dataset.step);b.dataset.day=n;b.disabled=n<0||n>=G.days.length;}else b.setAttribute('aria-pressed',String(Number(b.dataset.day)===day));});const select=dock.querySelector('select');if(select)select.value=day;dayStatus.textContent='第 '+(day+1)+' / '+G.days.length+' 天';
  let selected=-1;
  if(key==='itinerary')selected=Number($('#day-tabs [aria-pressed=true]')?.dataset.day??0);
  else if(key==='directory')selected=$('#saved-filter').getAttribute('aria-pressed')==='true'?1:0;
  else {const threshold=bar.getBoundingClientRect().bottom+32;items.forEach((x,i)=>{const e=x.target&&$('#'+x.target);if(e&&e.getBoundingClientRect().top<=threshold)selected=i;});}
  const active=key+':'+selected;
  if(active!==lastActive){lastActive=active;[...host.children].forEach((e,i)=>{const on=i===selected;e.classList.toggle('is-current',on);if(items[i].day!==undefined||items[i].action)e.setAttribute('aria-pressed',String(on));else if(on)e.setAttribute('aria-current','location');else e.removeAttribute('aria-current');});reveal(host.children[selected]);}
 }
 function jump(el){el?.scrollIntoView({behavior:reduced()?'instant':'smooth',block:'start'});}
 host.addEventListener('click',e=>{
  const button=e.target.closest('[data-context-index]');if(!button)return;const item=items[Number(button.dataset.contextIndex)];
  if(item.target){const target=$('#'+item.target);if(target?.tagName==='DETAILS')target.open=true;return;}
  if(item.day!==undefined){requestAnimationFrame(()=>{jump($('#day-view'));update($('#itinerary'));});}
  if(item.action){if(item.action==='all')$('[data-directory-reset]').click();else if($('#saved-filter').getAttribute('aria-pressed')!=='true')$('#saved-filter').click();jump($('#reader-search'));button.focus({preventScroll:true});requestAnimationFrame(()=>update($('#directory')));}
 });
 more.addEventListener('click',()=>more.dataset.back==='true'?host.scrollTo({left:0,behavior:reduced()?'instant':'smooth'}):host.scrollBy({left:Math.max(100,host.clientWidth*.7),behavior:reduced()?'instant':'smooth'}));
 host.addEventListener('scroll',overflow,{passive:true});addEventListener('resize',overflow);
 document.addEventListener('click',e=>{const b=e.target.closest('.mobile-day-dock [data-day],[data-next-day]');if(!b)return;requestAnimationFrame(()=>{jump($('#day-view'));update($('#itinerary'));if(b.hasAttribute('data-next-day')){const title=$('#day-view .day-title');title.tabIndex=-1;title.focus({preventScroll:true});}});});
 // External date changes (including the travel drawer) update the same selected day.
 document.addEventListener('journal:day',()=>{if(currentKey==='itinerary')update($('#itinerary'));});
 new MutationObserver(()=>{if(currentKey==='directory')update($('#directory'));}).observe($('#directory-areas'),{childList:true});
 window.MagazineReader={update};
})();
