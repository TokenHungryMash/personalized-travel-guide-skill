/* Three photographic gestures. Content pages and all district plates stay still. */
(()=>{'use strict';
 const root=document.documentElement,reduce=matchMedia('(prefers-reduced-motion: reduce)'),mobile=matchMedia('(max-width: 600px)');
 const scenes=[...document.querySelectorAll('.art-nightfall,.art-seaside,.art-afterdark')],visible=new Set();
 const properties=['--opening-inset','--opening-scale','--bay-depth','--night-offset'];
 let queued=false;
 const enabled=()=>root.dataset.motion!=='off'&&!reduce.matches&&!document.hidden;
 const clamp=n=>Math.max(0,Math.min(1,n));
 function draw(){
  queued=false;if(!enabled())return;
  const positions=[...visible].map(el=>[el,el.getBoundingClientRect()]);
  positions.forEach(([el,r])=>{
   if(el.matches('.art-nightfall')){const p=clamp((innerHeight*.95-r.top)/(innerHeight*.7));el.style.setProperty('--opening-inset',((1-p)*(mobile.matches?3:7)).toFixed(3)+'%');el.style.setProperty('--opening-scale',(1+(1-p)*.06).toFixed(4))}
   if(el.matches('.art-seaside')){const p=clamp((innerHeight-r.top)/(innerHeight+r.height));el.style.setProperty('--bay-depth',((p-.5)*(mobile.matches?20:66)).toFixed(2)+'px')}
   if(el.matches('.art-afterdark')){const p=clamp((innerHeight*.9-r.top)/(innerHeight*.85));el.style.setProperty('--night-offset',((1-p)*(mobile.matches?13:60)).toFixed(2)+'px')}
  });
 }
 function request(){if(!queued&&enabled()){queued=true;requestAnimationFrame(draw)}}
 function sync(){if(!enabled())scenes.forEach(el=>properties.forEach(p=>el.style.removeProperty(p)));else request()}
 if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{entries.forEach(e=>e.isIntersecting?visible.add(e.target):visible.delete(e.target));request()},{rootMargin:'80px',threshold:0});scenes.forEach(el=>observer.observe(el))}
 new MutationObserver(sync).observe(root,{attributes:true,attributeFilter:['data-motion']});
 reduce.addEventListener('change',sync);document.addEventListener('visibilitychange',sync);
 addEventListener('scroll',request,{passive:true});addEventListener('resize',request);sync();
})();
