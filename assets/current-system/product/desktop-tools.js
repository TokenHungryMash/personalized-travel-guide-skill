(function(){
  'use strict';
  const top=document.querySelector('.atlas-topbar');
  const search=top&&top.querySelector('.atlas-search-trigger');
  if(!top||!search||top.querySelector('.atlas-desktop-tools'))return;
  const tools=document.createElement('div');tools.className='atlas-desktop-tools';
  const button=document.createElement('button');
  button.type='button';button.className='atlas-desktop-adjust';button.setAttribute('aria-label','调整每日行程');
  button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 17h16M8 4v6M16 14v6"/></svg><span>调整行程</span>';
  button.onclick=()=>{
    if(window.BaliCustomizer&&typeof window.BaliCustomizer.open==='function') window.BaliCustomizer.open();
    else document.querySelector('.itinerary-customizer-launch')?.click();
  };
  const trip=document.querySelector('.trip-mode-launch');
  tools.appendChild(button);
  if(trip){trip.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 5 6-2 6 3 6-2v15l-6 2-6-3-6 2ZM9 3v15M15 6v15"/></svg><span>旅行模式</span>'; trip.removeAttribute('style');tools.appendChild(trip)}
  search.after(tools);
})();
