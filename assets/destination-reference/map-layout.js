/* Shared map data normalization and measured, screen-space label placement. */
(()=>{'use strict';
function normalize(map, places) {
 const ids = map.ids || [];
 const known = new Set(places.map(place => place.id));
 const projection = map.projection || {};
 const width = Number.isFinite(projection.width) && projection.width > 0 ? projection.width : 1400;
 const height = Number.isFinite(projection.height) && projection.height > 0 ? projection.height : 1100;
 const pins = (map.pins || []).filter(pin => known.has(pin.id) && ids.includes(pin.id)).map(pin => {
  const px = Number.isFinite(pin.px) ? pin.px : pin.x * width / 100;
  const py = Number.isFinite(pin.py) ? pin.py : pin.y * height / 100;
  return {...pin, px, py, x: px / width * 100, y: py / height * 100, number: ids.indexOf(pin.id) + 1};
 }).filter(pin => Number.isFinite(pin.px) && Number.isFinite(pin.py)
   && pin.px >= 0 && pin.px <= width && pin.py >= 0 && pin.py <= height);
 return {...map, ids, pins, projection: {...projection, width, height}, mappedIds: pins.map(pin => pin.id)};
}
const overlap=(a,b)=>a.left<b.right+4&&a.right>b.left-4&&a.top<b.bottom+4&&a.bottom>b.top-4;
function fitAtlas(art){const bounds=art.getBoundingClientRect();if(!bounds.width||!bounds.height)return;const labels=[...art.querySelectorAll('.atlas-pin-name')],occupied=[...art.querySelectorAll('.atlas-pin span')].map(e=>e.getBoundingClientRect());for(const el of labels){el.hidden=false;el.style.cssText='';const pin=el.closest('.atlas-pin').getBoundingClientRect(),w=el.getBoundingClientRect().width,h=el.getBoundingClientRect().height;let placed=false;for(const dy of [0,-16,16,-32,32,-48,48,-64,64]){for(const side of ['right','left']){el.style.position='absolute';el.style.right='auto';el.style.left=(side==='right'?pin.width/2+18:pin.width/2-18-w)+'px';el.style.top=(pin.height/2-h/2+dy)+'px';el.style.transform='none';const box=el.getBoundingClientRect();if(box.left>=bounds.left+3&&box.right<=bounds.right-3&&box.top>=bounds.top+3&&box.bottom<=bounds.bottom-3&&!occupied.some(b=>overlap(box,b))){occupied.push(box);placed=true;break}}if(placed)break}el.hidden=!placed}}
function fitOverview(svg){
 const bounds=svg.getBoundingClientRect();if(!bounds.width||!bounds.height)return;
 const width=svg.viewBox?.baseVal?.width||1400,scale=bounds.width/width,occupied=[];
 for(const g of svg.querySelectorAll('[data-map-dot]')){
  const c=g.querySelector('circle'),n=g.querySelector('[data-map-number]');
  c.setAttribute('r',Math.max(14,8/scale));n.setAttribute('font-size',Math.max(14,10/scale));n.setAttribute('y',Number(c.getAttribute('cy'))+3.5/scale);occupied.push(c.getBoundingClientRect());
 }
 for(const el of svg.querySelectorAll('[data-map-label]')){
  el.style.display='';el.setAttribute('font-size',Math.max(21,12/scale));
  const x=Number(el.dataset.px),y=Number(el.dataset.py);let placed=false,shifted=false;
  for(const offset of [0,-16,16,-32,32,-48,48,-64,64]){
   for(const side of [1,-1]){
    el.setAttribute('text-anchor',side===1?'start':'end');el.setAttribute('x',x+side*18/scale);el.setAttribute('y',y+(-10+offset)/scale);
    const b=el.getBoundingClientRect();
    if(b.left>=bounds.left+3&&b.right<=bounds.right-3&&b.top>=bounds.top+3&&b.bottom<=bounds.bottom-3&&!occupied.some(o=>overlap(b,o))){occupied.push(b);placed=true;shifted=offset!==0;break}
   }if(placed)break;
  }
  if(!placed)el.style.display='none';
  let line=el.parentNode.querySelector('[data-map-leader]');
  if(placed&&shifted){
   if(!line){line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('data-map-leader','');line.setAttribute('pointer-events','none');el.parentNode.insertBefore(line,el.parentNode.firstChild)}
   line.style.display='';line.setAttribute('x1',x);line.setAttribute('y1',y);line.setAttribute('x2',el.getAttribute('x'));line.setAttribute('y2',Number(el.getAttribute('y'))-4/scale);line.setAttribute('stroke','#586055');line.setAttribute('stroke-width',1/scale);line.setAttribute('opacity','.65');
  }else if(line)line.style.display='none';
 }
}
let queued=false,disposed=false,frame=0;const observed=new WeakSet(),ro=typeof ResizeObserver==='function'?new ResizeObserver(schedule):null;
function fit(){queued=false;document.querySelectorAll('.atlas-art,.journey-map-sheet svg').forEach(e=>{if(ro&&!observed.has(e)){ro.observe(e);observed.add(e)}if(e.matches('svg'))fitOverview(e);else fitAtlas(e)})}
function schedule(){if(!queued&&!disposed){queued=true;frame=requestAnimationFrame(fit)}}
const observer=new MutationObserver(schedule);observer.observe(document.documentElement,{childList:true,subtree:true});addEventListener('resize',schedule);document.addEventListener('toggle',schedule,true);document.addEventListener('journal:day',schedule);document.fonts?.ready.then(schedule);
document.addEventListener('click',e=>{if(e.target.closest('[data-overview-zoom],[data-map-zoom],[data-map-open]'))schedule()});
window.TravelMapLayout={normalize,fit:schedule,dispose(){disposed=true;cancelAnimationFrame(frame);observer.disconnect();ro?.disconnect()}};schedule();
})();
