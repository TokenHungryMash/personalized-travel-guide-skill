/* Explicit user-maintained reservation states; never infer that a venue confirmed. */
(function(){'use strict';
 function init(){
  var hard=document.querySelector('.audit-hard-times'),home=document.querySelector('#home'),cover=document.querySelector('#top');
  if(hard){if(home){var next=home.querySelector('.atlas-quickline');if(next)next.after(hard);else home.appendChild(hard)}else if(cover)cover.after(hard)}
  var list=document.querySelector('.audit-reservation-list'),sortButtons=Array.from(document.querySelectorAll('[data-reservation-sort]'));
  function sortReservations(mode){
   if(!list)return;
   var rows=Array.from(list.children);
   rows.sort(function(a,b){return (mode==='priority'?Number(a.dataset.priority)-Number(b.dataset.priority):0)||Number(a.dataset.order)-Number(b.dataset.order)});
   rows.forEach(function(row){list.appendChild(row)});
   sortButtons.forEach(function(button){button.setAttribute('aria-pressed',String(button.dataset.reservationSort===mode))});
   try{localStorage.setItem('bali-reservation-sort',mode)}catch(e){}
  }
  sortButtons.forEach(function(button){button.addEventListener('click',function(){sortReservations(button.dataset.reservationSort)})});
  var mode='priority';try{if(localStorage.getItem('bali-reservation-sort')==='date')mode='date'}catch(e){}sortReservations(mode);
  document.querySelectorAll('[data-reservation-id]').forEach(function(select){
   var key='bali-audit:'+select.dataset.reservationId;
   try{var saved=localStorage.getItem(key);if(saved&&Array.from(select.options).some(function(o){return o.value===saved}))select.value=saved}catch(e){}
   select.addEventListener('change',function(){try{localStorage.setItem(key,select.value)}catch(e){select.title='此浏览器无法保存状态，请自行记录'}});
  });
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
