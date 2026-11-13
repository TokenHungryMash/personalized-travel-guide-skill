/* Editorial choreography, without scroll interception or hidden base content. */
(()=>{'use strict';
 const root=document.documentElement,reduced=matchMedia('(prefers-reduced-motion: reduce)'),small=matchMedia('(max-width: 850px)');
 const running=new Set(),routeReveals=new Set(),ease='cubic-bezier(.22,1,.36,1)';
 let off=false;try{off=localStorage.getItem('fukuoka-motion')==='off'}catch(e){}
 const allowed=()=>!off&&!reduced.matches&&!document.hidden;
 function animate(el,frames,{duration=600,delay=0,...options}={}){
  if(!allowed()||!el?.animate)return null;
  const a=el.animate(frames,{duration:small.matches?Math.min(duration,480):duration,delay:small.matches?Math.min(delay,60):delay,easing:ease,...options});
  running.add(a);a.finished.catch(()=>{}).finally(()=>running.delete(a));return a;
 }
 function sync(){
  root.dataset.motion=off||reduced.matches?'off':'on';
  document.querySelectorAll('[data-motion-toggle]').forEach(b=>{b.textContent=off||reduced.matches?'动效：关':'动效：开';b.setAttribute('aria-pressed',String(!(off||reduced.matches)));b.setAttribute('aria-label','阅读动效');b.title=reduced.matches?'跟随系统减少动态效果偏好':'开关阅读动效'});
  if(off||reduced.matches){running.forEach(a=>a.cancel());running.clear();routeReveals.forEach(cleanup=>cleanup())}
 }
 sync();reduced.addEventListener('change',sync);
 document.addEventListener('click',e=>{if(e.target.closest('[data-motion-toggle]')){off=!off;try{localStorage.setItem('fukuoka-motion',off?'off':'on')}catch(e){}sync()}});
 document.addEventListener('visibilitychange',()=>running.forEach(a=>document.hidden?a.pause():a.play()));

 // Ordinary pages stay still. Only three photographic spreads have scroll choreography.
 // Keep the image wrappers used by the editorial crop rules, without entrance veils.
 document.querySelectorAll('.section-head').forEach(el=>{const line=document.createElement('span');line.className='chapter-rule';line.setAttribute('aria-hidden','true');el.append(line)});
 document.querySelectorAll('.fashion-opening-photo figure>img,.fashion-bleed figure>img,.fashion-night-layout figure>img,.fashion-afterword-photo figure>img').forEach(img=>{const frame=document.createElement('div'),shell=document.createElement('div');frame.className='editorial-image-frame';shell.className='image-drift-shell';img.before(frame);shell.append(img);frame.append(shell)});
 // Reveal route strokes through a mask, preserving the original solid/dashed legend.
 let routeSequence=0;
 function drawRoutes(){
  routeReveals.forEach(cleanup=>cleanup());
  if(!allowed())return;
  const svg=document.querySelector('#journey-overview svg');if(!svg)return;
  svg.querySelectorAll('polyline').forEach((line,i)=>{
   const length=line.getTotalLength?.();if(!length||!Number.isFinite(length))return;
   const ns='http://www.w3.org/2000/svg',mask=document.createElementNS(ns,'mask'),stroke=line.cloneNode(false),id='route-ink-'+(++routeSequence);
   mask.id=id;mask.setAttribute('maskUnits','userSpaceOnUse');mask.setAttribute('x','0');mask.setAttribute('y','0');mask.setAttribute('width','1400');mask.setAttribute('height','1100');
   stroke.removeAttribute('mask');stroke.setAttribute('stroke','white');stroke.setAttribute('stroke-width','12');stroke.setAttribute('opacity','1');stroke.setAttribute('stroke-linecap','round');stroke.setAttribute('stroke-dasharray',String(length));stroke.classList.add('route-drawing-stroke');
   mask.append(stroke);svg.append(mask);line.setAttribute('mask',`url(#${id})`);
   let animation;const cleanup=()=>{animation?.cancel();if(line.getAttribute('mask')===`url(#${id})`)line.removeAttribute('mask');mask.remove();routeReveals.delete(cleanup)};routeReveals.add(cleanup);
   animation=animate(stroke,[{strokeDashoffset:length},{strokeDashoffset:0}],{duration:1050,delay:i*90,fill:'backwards'});
   if(animation)animation.finished.catch(()=>{}).finally(cleanup);else cleanup();
  });
 }
 document.addEventListener('click',e=>{if(e.target.closest('[data-overview-day]'))drawRoutes()});
 // Expand the selected photograph from its cropped thumbnail, without stretching it.
 document.addEventListener('click',e=>{
  const source=e.target.closest('img[data-zoom]');if(!source||!allowed())return;
  const photo=document.querySelector('#photo-big'),dialog=document.querySelector('#photo-dialog'),from=source.getBoundingClientRect(),src=photo.src;
  if(!dialog.open||from.width<=0||from.height<=0)return;
  const expand=()=>{
   if(!dialog.open||photo.src!==src||!allowed())return;
   const to=photo.getBoundingClientRect();if(to.width<=0||to.height<=0)return;
   const scale=Math.max(from.width/to.width,from.height/to.height),cropX=Math.max(0,(to.width-from.width/scale)/2),cropY=Math.max(0,(to.height-from.height/scale)/2);
   const x=from.left-to.left-(to.width*scale-from.width)/2,y=from.top-to.top-(to.height*scale-from.height)/2;
   const a=animate(photo,[{transform:`translate(${x}px,${y}px) scale(${scale})`,clipPath:`inset(${cropY}px ${cropX}px)`},{transform:'translate(0,0) scale(1)',clipPath:'inset(0px 0px)'}],{duration:460});
   if(a){const stop=()=>a.cancel();dialog.addEventListener('close',stop,{once:true});a.finished.catch(()=>{}).finally(()=>dialog.removeEventListener('close',stop))}
  };
  if(photo.complete&&photo.naturalWidth)expand();else photo.addEventListener('load',expand,{once:true});
 });
 const progress=document.querySelector('.reading-progress'),label=document.querySelector('#reading-location'),chapters=[...document.querySelectorAll('.chapter')];let queued=false;
 function update(){
  queued=false;
  // Read geometry first, then update the small navigation indicators.
  const max=root.scrollHeight-innerHeight,ratio=max>0?Math.max(0,Math.min(1,scrollY/max)):0;
  let current=null;for(const c of chapters){if(c.getBoundingClientRect().top<=innerHeight*.32)current=c;else break}
  const timeline=document.querySelector('#day-view .timeline'),stops=timeline?[...timeline.querySelectorAll('.timeline-item')]:[],track=timeline?.getBoundingClientRect(),readingY=innerHeight*.36;
  const positions=stops.map(stop=>stop.getBoundingClientRect());let reading=-1;
  if(track&&track.height>0&&track.top<innerHeight&&track.bottom>0){positions.forEach((r,i)=>{if(r.top<readingY)reading=i});if(reading<0)reading=0}
  const trackProgress=track&&track.height>48?Math.max(0,Math.min(1,(readingY-track.top-24)/(track.height-48))):0;
  if(progress)progress.style.transform=`scaleX(${ratio})`;
  const chapterNames=['认识福冈','街区指南','四天行程','美食与餐厅','购物与伴手礼','景点与文化','地点库','实用贴士','行前准备','随身工具'];
  const title=current?(String(chapters.indexOf(current)+1).padStart(2,'0')+' / '+chapterNames[chapters.indexOf(current)]):'封面 / 福冈';
  if(label&&label.textContent!==title)label.textContent=title;
  document.querySelectorAll('.drawer-nav a').forEach(a=>{if(current&&a.hash==='#'+current.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')});
  const group=current?({itinerary:'days',directory:'places',fieldnotes:'tips',prepare:'tips',tools:'tips'}[current.id]||'city'):'';
  document.querySelectorAll('[data-reading-group]').forEach(a=>{a.classList.toggle('is-current',a.dataset.readingGroup===group);if(current&&a.hash==='#'+current.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')});
  timeline?.style.setProperty('--timeline-read',trackProgress.toFixed(4));stops.forEach((stop,i)=>stop.classList.toggle('is-reading',i===reading));
 }
 function request(){if(!queued){queued=true;requestAnimationFrame(update)}}
 addEventListener('scroll',request,{passive:true});addEventListener('resize',request);document.addEventListener('toggle',request,true);document.addEventListener('journal:day',request);document.addEventListener('journal:topic',request);document.fonts?.ready.then(request);update();
})();
