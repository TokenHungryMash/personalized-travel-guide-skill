(function(){
  'use strict';
  const modal=document.querySelector('#itinerary-customizer');
  if(!modal)return;
  const photo=modal.querySelector('.custom-photo-ref');
  const existing=modal.querySelector('.custom-existing');
  const timeline=existing&&existing.querySelector('.custom-timeline');
  if(photo&&existing&&timeline){
    const details=document.createElement('details');
    details.className='custom-photo-inline';
    details.innerHTML='<summary><span>参考样片</span><small>跟随当前日期保存，可选</small></summary><div class="custom-photo-inline-body"></div>';
    const body=details.querySelector('.custom-photo-inline-body');
    const picker=photo.querySelector('.custom-photo-add');
    const preview=photo.querySelector('.custom-photo-preview');
    if(picker)body.appendChild(picker);
    if(preview)body.appendChild(preview);
    timeline.after(details);
    photo.remove();
  }
  const freeform=modal.querySelector('.custom-freeform>header>b');
  if(freeform)freeform.textContent='04';
  const copy=modal.querySelector('[data-copy]');
  const download=modal.querySelector('[data-download]');
  if(copy)copy.textContent='复制修改内容';
  if(download)download.remove();
  const generated=modal.querySelector('.custom-request header small');if(generated)generated.remove();
  const actions=modal.querySelector('.itinerary-customizer__actions');if(actions)actions.style.gridTemplateColumns='1fr';
})();

// Keep light accordion headers readable in both open and closed states.
(()=>{document.querySelectorAll('#sights .mobile-section-fold>summary,#move .mobile-section-fold>summary,#food .food-chapter>summary,#shops .shop-region>summary').forEach(s=>{
 s.style.setProperty('background','#faf8f1','important');s.style.setProperty('color','#293e36','important');
 s.querySelectorAll('b,h3,strong').forEach(n=>{n.style.setProperty('color','#293e36','important');n.style.setProperty('-webkit-text-fill-color','#293e36','important');n.style.setProperty('text-shadow','none','important');n.style.setProperty('position','static','important')});
});})();
