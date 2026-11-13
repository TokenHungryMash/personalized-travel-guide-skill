/* Explicit, removable demonstration entries; never replace personal records. */
(()=>{'use strict';const prefix='journal-demo-',members=['我','演示·小林','演示·阿青'];let ctx,ready=false;
 const isDemo=x=>String(x.id).startsWith(prefix);
 function render(c){ctx=c;let host=document.querySelector('#ledger-demo');if(!host){host=document.createElement('section');host.id='ledger-demo';document.querySelector('.ledger-summary').prepend(host)}
 const count=c.state.expenses.filter(isDemo).length;
 host.innerHTML=`<p class="kicker">DEMO / 演示案例</p><h3>三个人，怎样一起记账？</h3><p>住宿、餐饮、交通与个人购物：5 笔虚构消费，含均分尾差、两种币种和一笔已还款。</p><div><button type="button" id="ledger-demo-load" ${count?'disabled':''}>${count?'已载入 '+count+' 笔演示账':'载入演示案例'}</button>${count?'<button type="button" id="ledger-demo-clear">移除演示账</button>':''}</div><small>金额仅用于功能演示，不是旅行报价；不会覆盖已有账目。</small><p id="ledger-demo-status" role="status"></p>`;
 if(ready)return;ready=true;
 document.addEventListener('click',e=>{const id=e.target.closest('button')?.id;if(!['ledger-demo-load','ledger-demo-clear'].includes(id))return;const s=ctx.state;let expenses=[...s.expenses],repayments=[...(s.repayments||[])],people=[...s.members],portraits={...s.memberAvatars},notes={...s.notes};
 if(id==='ledger-demo-load'){
  if(expenses.some(isDemo))return;notes.ledgerDemoMembers=JSON.stringify(members.filter(n=>!s.members.includes(n)));people=[...new Set([...people,...members])];if(people.length>30){document.querySelector('#ledger-demo-status').textContent='成员数量已满，无法加入演示成员。';return;}
  const base=ctx.G.edition.currency,other=base==='CNY'?'USD':'CNY',day=i=>ctx.G.days[Math.min(i,ctx.G.days.length-1)].id;
  const examples=[['双人住宿',9000,base,members[0],members.slice(0,2),'住宿',0],['三人午餐',2400,base,members[1],members,'餐饮',1],['三人交通 · 尾差示例',3001,base,members[2],members,'交通',1],['个人购物',1800,base,members[1],[members[1]],'购物',1],['行前通讯套餐',90,other,members[0],members,'其他',0]];
  expenses.push(...examples.map((x,i)=>({id:prefix+'expense-'+i,title:'演示 · '+x[0],amount:x[1],currency:x[2],payer:x[3],split:x[4],category:x[5],day:day(x[6]),method:i===2?'现金':'刷卡／电子支付',note:'虚构案例，仅演示记账功能',spentOn:'',date:new Date().toISOString()})));
  repayments.push({id:prefix+'repayment',from:members[1],to:members[0],amount:300,currency:base,date:new Date().toISOString()});
 }else{
  expenses=expenses.filter(x=>!isDemo(x));repayments=repayments.filter(x=>!isDemo(x));
  let added=[];try{added=JSON.parse(notes.ledgerDemoMembers||'[]')}catch{}if(!Array.isArray(added))added=[];delete notes.ledgerDemoMembers;people=people.filter(name=>!added.includes(name)||expenses.some(x=>x.payer===name||x.split.includes(name))||repayments.some(x=>x.from===name||x.to===name));
  for(const name of Object.keys(portraits))if(!people.includes(name))delete portraits[name];if(!people.length)people=['我'];
 }
 if(!ctx.saveDemo({members:people,expenses,repayments,memberAvatars:portraits,notes})){document.querySelector('#ledger-demo-status').textContent='保存失败，原账目保持不变。';return;}
 window.MagazineLedger.render(ctx);document.querySelector('#ledger-demo-status').textContent=id==='ledger-demo-load'?'案例已加入，可以查看明细、修改与结算。':'演示账已移除，其他账目保留。';
 });
 }
 window.LedgerDemo={render};
})();
