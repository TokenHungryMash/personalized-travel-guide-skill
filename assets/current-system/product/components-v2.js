/* Offline, mobile-first component layer. */
(() => {
 'use strict';
 const $=(s,c=document)=>c.querySelector(s), $$=(s,c=document)=>[...c.querySelectorAll(s)];
 const main=$('body>main');main.id='atlas-main';
 // Restore the actual original cover, including its typography and photograph.
 const cover=$('#top'),home=$('#home');
 if(cover&&home){cover.classList.remove('atlas-original');cover.hidden=false;$('.atlas-cover',home)?.replaceWith(cover);$('.atlas-home-title',home)?.remove();}
 $$('#atlas-main details:not(.day):not(.day-route-map)').forEach(fold=>{
  const summary=$(':scope > summary',fold);if(!summary)return;
  const title=$('b,h3',summary);if(!title)return;
  const kicker=$('small',summary);const meta=$('em',summary)||$$(':scope > span',summary).find(x=>!x.contains(title)&&x!==kicker&&x.textContent.trim());
  const copy=document.createElement('span');copy.className='atlas-fold-copy';
  if(kicker){kicker.className='atlas-fold-kicker';copy.append(kicker);}
  title.classList.add('atlas-fold-title');copy.append(title);
  if(meta){meta.classList.add('atlas-fold-meta');copy.append(meta);}
  const icon=document.createElement('i');icon.className='atlas-fold-icon';icon.setAttribute('aria-hidden','true');
  summary.replaceChildren(copy,icon);summary.classList.add('atlas-fold-summary');fold.classList.add('atlas-fold');
 });
 $$('.day-route-map').forEach((route,index)=>{
  route.classList.add('atlas-route');
  const summary=$(':scope>summary',route),title=$('.route-title',summary);
  if(title){const label=$('small',title);if(label)label.textContent='当天路线';}
  summary?.classList.add('atlas-route-summary');
  $$('.route-stop',route).forEach(stop=>{stop.setAttribute('aria-label',stop.textContent.replace(/\s+/g,' ').trim()+'，打开地图');});
  const track=$('.route-map-track',route);if(track){track.setAttribute('aria-label','按顺序排列的路线地点');track.tabIndex=0;}
 });
 // Keep the mobile screen clear: high-frequency actions live in one stable toolbar.
 const dock=document.createElement('nav');dock.className='atlas-mobile-dock';dock.setAttribute('aria-label','随身工具');
 dock.innerHTML='<a href="#home" aria-label="旅行首页"><svg viewBox="0 0 24 24"><path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-8h6v8"/></svg><span>首页</span></a><button data-dock="chapters"><svg viewBox="0 0 24 24"><path d="M8 6h13M8 12h13M8 18h13M3 6h1M3 12h1M3 18h1"/></svg><span>目录</span></button><button data-dock="trip"><svg viewBox="0 0 24 24"><path d="m3 5 6-2 6 3 6-2v15l-6 2-6-3-6 2ZM9 3v15M15 6v15"/></svg><span>旅行</span></button><button data-dock="search"><svg viewBox="0 0 24 24"><circle cx="10" cy="10" r="6.5"/><path d="m15 15 6 6"/></svg><span>搜索</span></button><button data-dock="edit"><svg viewBox="0 0 24 24"><path d="M4 7h16M4 17h16M8 4v6M16 14v6"/></svg><span>调整</span></button>';
 document.body.append(dock);
 dock.onclick=e=>{const action=e.target.closest('[data-dock]')?.dataset.dock;if(action==='trip')$('.trip-mode-launch')?.click();if(action==='search')$('.atlas-search-trigger')?.click();if(action==='edit')$('.itinerary-customizer-launch')?.click();if(action==='chapters')$('.atlas-menu-toggle')?.click();};
 document.addEventListener('click',e=>{const back=e.target.closest('.back-to-contents');if(!back||!matchMedia('(max-width:800px)').matches)return;e.preventDefault();document.body.classList.add('atlas-menu-open');$('.atlas-menu-toggle')?.setAttribute('aria-expanded','true');});
 const scrim=document.createElement('button');scrim.className='atlas-menu-scrim';scrim.setAttribute('aria-label','关闭章节目录');scrim.onclick=()=>{document.body.classList.remove('atlas-menu-open');$('.atlas-menu-toggle')?.setAttribute('aria-expanded','false');};document.body.append(scrim);
 function locationState(){const id=location.hash.slice(1)||'home';document.body.dataset.atlasChapter=id;}
 window.addEventListener('hashchange',locationState);locationState();
 // Web Animations are progressive enhancement; reduced-motion users get instant changes.
 const reduce=matchMedia('(prefers-reduced-motion: reduce)');
 document.addEventListener('toggle',e=>{const fold=e.target;if(!(fold instanceof HTMLDetailsElement)||!fold.open||reduce.matches||!fold.closest('#atlas-main'))return;const body=[...fold.children].filter(x=>x.tagName!=='SUMMARY');body.forEach(el=>{el.getAnimations().forEach(a=>a.cancel());el.animate([{opacity:.35,transform:'translateY(6px)'},{opacity:1,transform:'translateY(0)'}],{duration:200,easing:'cubic-bezier(.16,1,.3,1)'});});},true);
 window.addEventListener('hashchange',()=>{if(reduce.matches||matchMedia('(max-width:800px)').matches)return;requestAnimationFrame(()=>{const page=$('#atlas-main>:not([hidden])');if(page)page.animate([{opacity:.5,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}],{duration:220,easing:'cubic-bezier(.16,1,.3,1)'});});});
 function chevron(summary){if($(':scope>.atlas-chevron',summary))return;const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.classList.add('atlas-chevron');svg.innerHTML='<path d="m6 9 6 6 6-6"/>';summary.append(svg);}
 $$('.atlas-fold-summary,.day>summary').forEach(chevron);
 $$('.atlas-fold').forEach((fold,index)=>{
  const summary=$(':scope>summary',fold);if(!summary)return;
  const photo=$(':scope>:not(summary) img',fold);
  if(photo&&photo.getAttribute('src')){const media=document.createElement('span');media.className='atlas-fold-media';const img=document.createElement('img');img.src=photo.getAttribute('src');img.alt='';img.loading='lazy';media.append(img);summary.prepend(media);summary.classList.add('has-media');}
  else{const mark=document.createElement('span');mark.className='atlas-fold-mark';mark.setAttribute('aria-hidden','true');mark.innerHTML='<svg viewBox="0 0 24 24"><path d="M5 4h10l4 4v12H5ZM14 4v5h5M8 12h8M8 16h6"/></svg>';summary.prepend(mark);}
 });
 const tripObserver=new MutationObserver(()=>{$$('.trip-day-map>summary,.trip-shopping-tip>summary').forEach(chevron);});tripObserver.observe(document.body,{childList:true,subtree:true});
 document.addEventListener('click',e=>{if(e.target.closest('[data-close-trip]'))$('.trip-mode-close')?.click();},true);
})();
