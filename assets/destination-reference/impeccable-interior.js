/* Put totals and actions first in DOM order as well as visual order; preserve all state and listeners. */
(()=>{'use strict';
 function arrange(){
  const summary=document.querySelector('#ledger-dialog .ledger-summary');
  if(!summary)return;
  const totals=summary.querySelector('#ledger-totals'),jump=summary.querySelector('.ledger-jump'),demo=document.querySelector('#ledger-demo');
  if(totals&&summary.firstElementChild!==totals)summary.prepend(totals);
  if(totals&&jump&&totals.nextElementSibling!==jump)totals.after(jump);
  const form=document.querySelector('#expense-form');
  if(form&&demo&&form.nextElementSibling!==demo)form.after(demo);
  if(!summary.querySelector('.ledger-help')){
   const help=document.createElement('details');help.className='ledger-help';help.innerHTML='<summary>记账说明与汇率换算</summary>';
   summary.querySelectorAll(':scope > p.small,.fx-box').forEach(e=>help.append(e));summary.append(help);
  }
  if(form&&!form.querySelector('.ledger-extra')){
   const extra=document.createElement('details');extra.className='ledger-extra';extra.innerHTML='<summary>补充日期、支付方式与备注</summary><div class="form-grid"></div>';
   form.querySelector('fieldset').after(extra);
  }
  if(form){
   const extra=form.querySelector('.ledger-extra');
   for(const name of ['spentOn','method','note']){const label=form.elements[name]?.closest('label');if(label&&!extra.contains(label))extra.lastElementChild.append(label)}
   const grid=form.querySelector('.form-grid'),currency=form.elements.currency?.closest('label'),amount=form.elements.amount?.closest('label');
   if(currency&&amount&&amount.nextElementSibling!==currency)amount.after(currency);
   form.elements.title.closest('label').classList.add('ledger-title-field');
  }
 }
 arrange();document.addEventListener('journal:day',arrange);
 const summary=document.querySelector('#ledger-dialog .ledger-summary');
 if(summary)new MutationObserver(arrange).observe(summary,{childList:true});
 document.addEventListener('click',e=>{if(e.target.closest('[data-edit-expense]')){const extra=document.querySelector('.ledger-extra');if(extra)extra.open=true}});
})();
