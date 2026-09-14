/* Independent offline reading shell. Original trip, checklist and place logic remain intact. */
(() => {
 const $=(s,c=document)=>c.querySelector(s), $$=(s,c=document)=>[...c.querySelectorAll(s)];
 const chapters=[['route','九日行程','路线与每日安排'],['stay','航班与住宿','航班时间与两处住宿'],['sights','景点','景点、自然与海岸'],['food','餐饮指南','餐厅、外卖与菜单'],['shops','购物指南','品牌与当地好物'],['move','当地特色体验','运动、SPA 与冒险'],['booking','出发前准备','预约与行李清单'],['words','语言锦囊','英语与印尼语'],['tips','旅游贴士','在岛上的实用提醒']];
 const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 document.body.classList.add('atlas-ui');
 const main=$('body > main');
 const stayFold=$('.hotel-chapter-fold');if(stayFold){const stay=$('#stay',stayFold);if(stay)stayFold.replaceWith(stay);}
 const flight=$('.flight-band');if(flight){flight.id='flights';const stay=document.getElementById('stay');if(stay)stay.append(flight);}
 const menu=$('#food .menu-field-page');if(menu){const fold=document.createElement('details');fold.className='atlas-menu-guide';fold.innerHTML='<summary><span><b>点餐时，随手查</b><small>菜单词汇 · 辣度 · 过敏原 · 账单</small></span><span>展开 ＋</span></summary>';menu.before(fold);fold.append(menu);}
 [...main.children].forEach(n=>n.classList.add('atlas-original'));
 const sidebar=document.createElement('aside');sidebar.className='atlas-sidebar';
 sidebar.innerHTML=``;
 document.body.prepend(sidebar);
 const top=document.createElement('header');top.className='atlas-topbar';top.innerHTML='<button class="atlas-menu-toggle" aria-label="展开章节目录" aria-expanded="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14M5 12h14M5 18h14"/></svg></button><span class="atlas-breadcrumb">我们的旅行 / <b>旅行首页</b></span><button class="atlas-search-trigger"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><span>搜索手册</span><kbd>Ctrl K</kbd></button>';
 main.before(top);
 const home=document.createElement('div');home.id='home';home.className='atlas-home';
 home.innerHTML=``;
 main.prepend(home);
 $$('#route .day').forEach((day,i)=>{
  const summary=$('summary',day);if(!summary)return;
  if(!day.id)day.id='atlas-day-'+(i+1);
  const a=document.createElement('a');a.href='#'+day.id;
  a.innerHTML=`<span class="atlas-day-num">${String(i+1).padStart(2,'0')}</span><div><small>${escape(($('small',summary)||{}).textContent||'')}</small><b>${escape(($('b',summary)||{}).textContent||'今日行程')}</b></div><span class="atlas-day-excerpt">${escape(($('em',summary)||{}).textContent||'')}</span><span>↗</span>`;
  $('.atlas-day-list',home).append(a);
 });
 const dialog=document.createElement('dialog');dialog.className='atlas-search';dialog.innerHTML='<div class="atlas-search-head"><input type="search" aria-label="搜索手册内容" placeholder="找餐厅、景点、行李或某一天…"><button aria-label="关闭搜索">✕</button></div><p class="atlas-search-hint">搜索整本手册 · 无需联网</p><div class="atlas-search-results"></div>';
 document.body.append(dialog);
 const entries=[];
 chapters.forEach(([id,label])=>{
  const section=$('#'+id);if(!section)return;
  $$('h3, .day > summary, .tip, .check-item, .vocab',section).forEach((el,i)=>{
   const context=el.closest('article, details, .restaurant, .vocab')||el.parentElement;
   if(!el.id)el.id=`atlas-find-${id}-${i}`;
   entries.push({id:el.id,label,title:el.textContent.trim().replace(/\s+/g,' ').slice(0,110),text:context.textContent.toLowerCase(),element:el});
  });
  entries.push({id,label,title:label,text:section.textContent.toLowerCase(),element:section});
 });
 function results(){const q=$('input',dialog).value.trim().toLowerCase();const hits=q?entries.filter(e=>e.text.includes(q)||e.title.toLowerCase().includes(q)).slice(0,35):entries.filter(e=>chapters.some(c=>c[0]===e.id));$('.atlas-search-results',dialog).innerHTML=hits.length?hits.map(e=>`<a href="#${e.id}"><small>${escape(e.label)}</small><b>${escape(e.title)}</b><span>↗</span></a>`).join(''):'<p class="atlas-empty">没有找到相关内容，试试「乌布」「餐厅」或「行李」。</p>';}
 function openSearch(){results();dialog.showModal();$('input',dialog).focus();}
 $('.atlas-search-trigger').onclick=openSearch;$('input',dialog).oninput=results;$('button',dialog).onclick=()=>dialog.close();
 dialog.onclick=e=>{if(e.target===dialog)dialog.close();if(e.target.closest('a'))dialog.close();};
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openSearch();}});
 $('.atlas-menu-toggle').onclick=()=>{const open=document.body.classList.toggle('atlas-menu-open');$('.atlas-menu-toggle').setAttribute('aria-expanded',open);};
 $('.atlas-trip-open').onclick=()=>(function(e){if(e)e.click();}($('.trip-mode-launch')));
 const mobileReading=matchMedia('(max-width:800px)');
 // Put the continuous reading order in the same order as the directory.
 chapters.forEach(([id])=>{const section=document.getElementById(id);if(section&&section.parentElement===main)main.append(section);});
 function navigate(){let id;try{id=decodeURIComponent(location.hash.slice(1))||'home';}catch(e){id='home';}let target=document.getElementById(id);const chapter=target&&target.closest('main > section');let active=chapter&&chapter.id|| (id==='home'?'home':null);if(!active){active='home';target=home;}
  $$('.atlas-original',main).forEach(n=>n.hidden=mobileReading.matches?!chapters.some(c=>c[0]===n.id):n!==chapter);home.hidden=mobileReading.matches?false:active!=='home';
  if(chapter){let n=target;while(n&&n!==chapter){if(n.tagName==='DETAILS')n.open=true;n=n.parentElement;}}
  $$('.atlas-sidebar [data-page]').forEach(a=>{const selected=a.dataset.page===active;a.classList.toggle('is-active',selected);if(selected)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  $('.atlas-breadcrumb b').textContent=(chapters.find(c=>c[0]===active)||[])[1]||'旅行首页';
  document.body.classList.remove('atlas-menu-open');$('.atlas-menu-toggle').setAttribute('aria-expanded','false');
  requestAnimationFrame(()=>{if(target&&target!==home&&(mobileReading.matches||target!==chapter))target.scrollIntoView({block:'start'});else window.scrollTo(0,0);});
 }
 window.addEventListener('hashchange',navigate);mobileReading.addEventListener('change',navigate);navigate();
 let scrollQueued=false;
 window.addEventListener('scroll',()=>{if(!mobileReading.matches||scrollQueued)return;scrollQueued=true;requestAnimationFrame(()=>{scrollQueued=false;let current='home';for(const [id] of chapters){const section=document.getElementById(id);if(section&&section.getBoundingClientRect().top<=150)current=id;}
 $('.atlas-breadcrumb b').textContent=(chapters.find(c=>c[0]===current)||[])[1]||'旅行首页';document.body.dataset.atlasChapter=current;
 $$('.atlas-sidebar [data-page]').forEach(a=>{const selected=a.dataset.page===current;a.classList.toggle('is-active',selected);if(selected)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
 });},{passive:true});
 // Keep a stable checklist key: original labels change from pending to confirmed.
 const checklistKey='bali-atlas-checklist-20260907';
 function restoreChecklist(){try{const saved=JSON.parse(localStorage.getItem(checklistKey)||'null');if(!Array.isArray(saved))return;$$('#booking input[type="checkbox"]').forEach((input,i)=>{input.checked=!!saved[i];var li=input.closest('li');if(li)li.classList.toggle('is-packed',input.checked);});if(typeof window.updatePacking==='function')window.updatePacking();}catch(e){}}
 document.addEventListener('change',e=>{if(!e.target.matches('#booking input[type="checkbox"]'))return;try{localStorage.setItem(checklistKey,JSON.stringify($$('#booking input[type="checkbox"]').map(x=>x.checked)));}catch(e){};});
 window.addEventListener('pageshow',()=>requestAnimationFrame(restoreChecklist));requestAnimationFrame(restoreChecklist);
})();
