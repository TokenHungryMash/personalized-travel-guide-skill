/* Tokyo editorial motion: ink registration, three distinct photographic gestures.
 * Uses the bundled GSAP core; no requests, scroll interception or hidden base state. */
(()=>{'use strict';
 const g=window.gsap,root=document.documentElement,reduce=matchMedia('(prefers-reduced-motion: reduce)'),small=matchMedia('(max-width:700px)');
 const scenes=[...document.querySelectorAll('.ink-scene')].slice(0,3),visible=new Set();
 let context=null,tracks=[],queued=false,coverPlayed=false,dayTween=null;
 const enabled=()=>!!g&&root.dataset.motion!=='off'&&!reduce.matches&&!document.hidden;
 const permitted=()=>!!g&&root.dataset.motion!=='off'&&!reduce.matches;
 function reset(){context?.revert();context=null;tracks=[];dayTween=null;scenes.forEach(e=>{e.style.removeProperty('--photo-drift');e.style.removeProperty('--type-drift')});}
 function setup(){
  reset();if(!permitted())return;
  context=g.context(()=>{
   const title=document.querySelector('#cover-title'),city=document.querySelector('.cover-city'),cover=document.querySelector('#cover');
   if(!coverPlayed&&cover&&cover.getBoundingClientRect().bottom>0){
    coverPlayed=true;
    const tl=g.timeline({defaults:{ease:'expo.out',duration:.8}});
    // The two printed colours settle into registration while the night remains still.
    if(title)tl.fromTo(title,{x:small.matches?-10:-24,opacity:.8,textShadow:'7px 0px 0px rgba(237,151,62,.55)'},{x:0,opacity:1,textShadow:'0px 0px 0px rgba(237,151,62,0)',clearProps:'transform,opacity,textShadow'},0);
    if(city)tl.fromTo(city,{x:small.matches?10:24,opacity:.7},{x:0,opacity:1,clearProps:'transform,opacity'},.08);
    const footer=document.querySelector('.cover-ink-footer');
    if(footer)tl.fromTo(footer,{opacity:.7},{opacity:1,duration:.35,clearProps:'opacity'},.3);
   }
   const drift=small.matches?12:32,type=small.matches?8:27;
   tracks=scenes.map((scene,i)=>{
    const tl=g.timeline({paused:true,defaults:{ease:'none'}});
    if(i===0){ // Street movement: the two overprinted lines cross in opposite directions.
     tl.fromTo(scene,{'--type-drift':-type+'px'},{'--type-drift':type+'px',duration:1});
    }else if(i===1){ // Architectural spread: a small vertical move through the photograph.
     tl.fromTo(scene,{'--photo-drift':drift+'px'},{'--photo-drift':-drift+'px',duration:1});
    }else{ // Night spread: the lettering holds as the photograph changes register.
     tl.fromTo(scene,{'--photo-drift':-drift*.6+'px','--type-drift':type*.5+'px'},{'--photo-drift':drift*.6+'px','--type-drift':-type*.5+'px',duration:1});
    }
    return {scene,tl};
   });
  });request();
 }
 function draw(){queued=false;if(!enabled())return;
  const positions=tracks.filter(x=>visible.has(x.scene)).map(x=>[x,x.scene.getBoundingClientRect()]);
  positions.forEach(([x,r])=>x.tl.progress(Math.max(0,Math.min(1,(innerHeight-r.top)/(innerHeight+r.height)))));
 }
 function request(){if(!queued&&enabled()){queued=true;requestAnimationFrame(draw)}}
 function sync(){if(!permitted())reset();else if(!context)setup();else request();}
 const observer=new IntersectionObserver(entries=>{entries.forEach(e=>e.isIntersecting?visible.add(e.target):visible.delete(e.target));request()},{rootMargin:'30px'});
 scenes.forEach(e=>observer.observe(e));
 new MutationObserver(sync).observe(root,{attributes:true,attributeFilter:['data-motion']});
 reduce.addEventListener('change',sync);small.addEventListener('change',setup);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)reset();else sync()});
 addEventListener('scroll',request,{passive:true});addEventListener('resize',request);
 document.addEventListener('journal:day',()=>{if(!enabled()||!context)return;
  const panel=document.querySelector('#day-view .day-opening');if(!panel)return;
  dayTween?.revert();
  context.add(()=>{dayTween=g.fromTo(panel,{x:small.matches?4:8,opacity:.78},{x:0,opacity:1,duration:.22,ease:'power2.out',clearProps:'transform,opacity'});});
 });
 window.MagazineMotion={sceneCount:scenes.length,enabled,engine:g?'GSAP '+g.version:'static',get activeTracks(){return tracks.length}};
 setup();
})();
