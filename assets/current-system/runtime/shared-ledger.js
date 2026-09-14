(()=>{
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
window.createSharedLedger=cloud=>{
 const el=document.createElement('section');el.className='expense-app shared-ledger';
 el.innerHTML=`<header><small>OUR TRIP · ${cloud.local?'本机账本':'共享账本'}</small><h2>旅行记账</h2></header>${cloud.local?'<p>本地文件仅保存到这台设备。多人同步请打开云端手册。</p>':''}
 <div class="ledger-sync"><button type="button" data-refresh>刷新</button><span data-sync role="status">正在连接…</span></div>
 <details class="ledger-members" open><summary>旅行成员 <span data-count></span></summary><p>先添加姓名，可上传头像。每笔选择付款人和分摊成员，默认均分。</p><div data-members class="member-list"></div>
 <form class="member-form"><label>姓名<input name="name" maxlength="20" placeholder="例如：你的名字" required></label><label>头像（可选）<input name="avatar" type="file" accept="image/*"></label><button type="submit">添加成员</button><button type="button" data-member-cancel hidden>取消</button><span role="status" data-member-status></span></form></details>
 <section class="settlement-box"><h3>现在怎么结算</h3><p>按币种分别结算，不自动换汇；已登记的还款会抵扣欠款。</p><div data-settlements></div></section>
 <div class="expense-totals"></div>
 <form class="expense-form"><label>金额<input name="amount" type="number" min="0.01" max="10000000000" step="0.01" inputmode="decimal" placeholder="0.00" required></label><label>币种<select name="currency"><option>KRW</option><option>IDR</option><option>CNY</option><option>USD</option><option>HKD</option></select></label><label>日期<input name="date" type="date" required></label><label>类别<select name="category"><option>餐饮</option><option>交通</option><option>住宿</option><option>门票与体验</option><option>购物</option><option>其他</option></select></label><label>谁付的钱<select name="payer" required></select></label><label>支付方式<select name="method"><option value="刷卡／电子支付">刷卡 / 电子</option><option>现金</option></select></label><fieldset class="split-members"><legend>谁一起分摊 · 所选成员均分</legend><div data-splits></div><small>分到分，余数按固定成员编号分配，合计始终等于总额。</small></fieldset><label class="expense-note">备注<input name="note" maxlength="120" placeholder="例如：两个人的晚餐"></label><button type="submit">保存这笔</button><button type="button" data-cancel hidden>取消修改</button></form>
 <p class="expense-status" role="status"></p><h3>账目与还款记录</h3><div class="expense-list"></div>`;
 const $=s=>el.querySelector(s),form=$('.expense-form'),mf=$('.member-form');
 const fx=document.createElement('details');fx.className='exchange-tool';fx.innerHTML='<summary><b>汇率换算</b><span>展开 ＋</span></summary><div class="exchange-tool-body"><div class="exchange-main"><label>原币金额<span><input data-fx-amount type="number" min="0" step="0.01" value="10000"><select data-fx-from aria-label="原币种"><option>KRW</option><option>CNY</option><option>USD</option><option>HKD</option><option>IDR</option></select></span></label><label>换算结果<span class="exchange-result"><output data-fx-result>52.00</output><select data-fx-to aria-label="目标币种"><option>CNY</option><option>KRW</option><option>USD</option><option>HKD</option><option>IDR</option></select></span></label></div><label class="exchange-rate">参考汇率<span>1 原币 = <input data-fx-rate aria-label="一单位原币对应的目标币金额" type="number" min="0.000001" step="0.000001" value="0.0052"> 目标币</span></label><button type="button" data-fx-refresh>自动校准</button><small data-fx-status>联网时自动读取最新参考汇率，也可手动修改。</small></div>';
 el.insertBefore(fx,$('.ledger-members'));
 const fxAmount=$('[data-fx-amount]'),fxFrom=$('[data-fx-from]'),fxTo=$('[data-fx-to]'),fxRate=$('[data-fx-rate]'),fxResult=$('[data-fx-result]'),fxRefresh=$('[data-fx-refresh]'),fxStatus=$('[data-fx-status]');
 const fxStoreKey='travel-ledger-fx:'+(window.HANDBOOK_CONFIG?.slug||document.title||location.pathname);
 function renderFx(){const amount=Number(fxAmount.value)||0,rate=Number(fxRate.value)||0;fxResult.textContent=Number(amount*rate).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});try{localStorage.setItem(fxStoreKey,JSON.stringify({from:fxFrom.value,to:fxTo.value,rate:rate}))}catch(e){}}
async function calibrateFx(force){const from=fxFrom.value,to=fxTo.value;if(from===to){fxRate.value='1';fxStatus.textContent='同币种汇率为 1';renderFx();return}const cacheKey=fxStoreKey+':latest:'+from+':'+to;try{const cached=JSON.parse(localStorage.getItem(cacheKey)||'null');if(!force&&cached&&Date.now()-cached.savedAt<21600000){fxRate.value=cached.rate;fxStatus.textContent='参考汇率 · '+cached.date+' 更新';renderFx();return}}catch(e){}fxRefresh.disabled=true;fxStatus.textContent='正在获取最新参考汇率…';try{const res=await fetch('https://api.frankfurter.dev/v2/rate/'+encodeURIComponent(from)+'/'+encodeURIComponent(to),{cache:'no-store'});if(!res.ok)throw Error('rate');const data=await res.json();if(!Number.isFinite(Number(data.rate)))throw Error('rate');fxRate.value=Number(data.rate).toFixed(Number(data.rate)<.01?6:4);try{localStorage.setItem(cacheKey,JSON.stringify({rate:fxRate.value,date:data.date,savedAt:Date.now()}))}catch(e){}fxStatus.textContent='参考汇率 · '+data.date+' 更新';renderFx()}catch(e){fxStatus.textContent='暂时无法自动校准，可继续手动填写'}finally{fxRefresh.disabled=false}}
 try{const saved=JSON.parse(localStorage.getItem(fxStoreKey)||'null');if(saved){fxFrom.value=saved.from||fxFrom.value;fxTo.value=saved.to||fxTo.value;fxRate.value=saved.rate||fxRate.value}}catch(e){}
 ;[fxAmount,fxRate].forEach(x=>x.addEventListener('input',renderFx));[fxFrom,fxTo].forEach(x=>x.addEventListener('change',()=>calibrateFx(true)));fxRefresh.addEventListener('click',()=>calibrateFx(true));renderFx();calibrateFx(false);
 let members=[],records=[],loaded=false,busy=false,editing=null,memberEditing=null,transfers=[],draftId=null,memberDraftId=null,formMembers='',selectionTouched=false,initial=true;
 const member=id=>members.find(m=>m.id===id),name=id=>member(id)?.name||'待确认付款人',money=n=>Number(n).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
 const avatar=m=>m.avatar?`<img src="${esc(m.avatar)}" alt="" width="32" height="32">`:`<span class="member-initial" aria-hidden="true">${esc(m.name.slice(0,1))}</span>`;
 const identity=id=>{const m=member(id)||{name:'待确认付款人',avatar:''};return `<span class="settlement-party">${avatar(m)}<b>${esc(m.name)}</b></span>`};
 const today=()=>new Date().toLocaleDateString('en-CA');
 function selectMembers(){
  const signature=JSON.stringify(members.map(m=>[m.id,m.name]));if(signature===formMembers)return;formMembers=signature;
  const payer=form.elements.payer.value,selected=new Set([...el.querySelectorAll('[name=participant]:checked')].map(x=>x.value));
  form.elements.payer.innerHTML=members.map(m=>`<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');if(members.some(m=>m.id===payer))form.elements.payer.value=payer;
  $('[data-splits]').innerHTML=members.map(m=>`<label><input type="checkbox" name="participant" value="${esc(m.id)}" ${!selectionTouched||selected.has(m.id)?'checked':''}>${avatar(m)}<span>${esc(m.name)}</span></label>`).join('');
 }
 function render(){
  selectMembers();$('[data-count]').textContent=`${members.length} 人`;
  $('[data-members]').innerHTML=members.map(m=>`<button type="button" data-member="${esc(m.id)}">${avatar(m)}<span>${esc(m.name)}</span><small>编辑</small></button>`).join('');
  const totals=window.calculateTravelSettlement(records,members);transfers=[];
  $('.expense-totals').innerHTML=Object.entries(totals).map(([c,s])=>`<span>已花 ${esc(c)} <b>${money(s.total/100)}</b></span>`).join('');
  $('[data-settlements]').innerHTML=Object.entries(totals).map(([c,s])=>`<div class="currency-settlement"><b>${esc(c)}</b>${s.unresolved?`<p>有 ${s.unresolved} 笔旧记录未明确付款人，请点击该笔“修改”后再结算。</p>`:s.transfers.length?s.transfers.map(t=>{const index=transfers.push({...t,currency:c})-1;return `<div class="settlement-row"><span class="settlement-parties">${identity(t.from)}<i aria-hidden="true">→</i>${identity(t.to)}</span><strong>${money(t.amount)}</strong><button type="button" data-settle="${index}">登记还款</button></div>`}).join(''):'<p>已结清，不需要转账。</p>'}${s.unresolved?'':`<details><summary>查看每人净额</summary>${Object.entries(s.balances).map(([id,n])=>`<p>${esc(name(id))} · ${n>0?'应收':n<0?'应付':'已平'} ${money(Math.abs(n)/100)}</p>`).join('')}</details>`}</div>`).join('')||`<p>${!loaded?'正在读取…':members.length<2?'添加旅行成员，再记下第一笔。':'还没有账目，记账后会自动算出谁给谁多少钱。'}</p>`;
  $('.expense-list').innerHTML=records.slice().sort((a,b)=>b.date.localeCompare(a.date)||b.updated_at.localeCompare(a.updated_at)).map(r=>`<article><div><b>${esc(r.kind==='settlement'?'还款 · '+name(r.payer)+' → '+name(r.participants[0]):r.note||r.category)}</b><small>${esc(r.date)} · ${r.kind==='settlement'?'已登记还款':esc(name(r.payer))+' 付款 · '+r.participants.map(id=>esc(name(id))).join('、')+'均分'}</small></div><strong>${esc(r.currency)} ${money(r.amount)}</strong><div class="ledger-record-actions">${r.kind==='settlement'?'':`<button type="button" data-edit="${esc(r.id)}">修改</button>`}<button type="button" data-delete="${esc(r.id)}">${r.kind==='settlement'?'撤销':'删除'}</button></div></article>`).join('')||'<p>暂无记录。</p>';
  form.querySelector('[type=submit]').disabled=busy||!loaded||!members.length;
  el.querySelectorAll('[data-edit],[data-delete],[data-settle]').forEach(b=>b.disabled=busy);
 }
 async function refresh(){try{await cloud.refresh();}catch(e){$('[data-sync]').textContent='未同步 · 请联网后刷新';if(!loaded)$('.expense-status').textContent=e.message;}}
 cloud.subscribe(state=>{members=state.members||[];records=state.expenses;loaded=true;render();$('[data-sync]').textContent=(cloud.local?'已读取本机 ':'已同步 ')+new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',second:'2-digit'});if(initial){initial=false;if(members.length>=2)$('.ledger-members').open=false;}});
 $('[data-refresh]').onclick=refresh;
 function reset(){editing=null;draftId=null;selectionTouched=false;form.reset();form.elements.date.value=today();el.querySelectorAll('[name=participant]').forEach(x=>x.checked=true);form.querySelector('[type=submit]').textContent='保存这笔';$('[data-cancel]').hidden=true;}
 $('[data-cancel]').onclick=reset;
 form.addEventListener('change',e=>{if(e.target.name==='participant')selectionTouched=true;});
 async function write(record){await cloud.putExpense(record);await refresh();}
 form.onsubmit=async e=>{e.preventDefault();if(busy||!loaded)return;const f=new FormData(form),participants=f.getAll('participant');if(!participants.length){$('.expense-status').textContent='请至少选择一位分摊成员。';return;}
  const r={...Object.fromEntries(f),amount:Number(f.get('amount')),participants,kind:'expense',id:editing?.id||(draftId??=crypto.randomUUID()),version:editing?.version||0};delete r.participant;
  busy=true;render();$('.expense-status').textContent='正在保存…';try{await write(r);reset();$('.expense-status').textContent='已保存，结算结果已更新。';}catch(error){$('.expense-status').textContent=error.message+' 输入已保留。';}finally{busy=false;render();}
 };
 el.addEventListener('click',async e=>{
  const edit=e.target.closest('[data-edit]'),del=e.target.closest('[data-delete]'),settle=e.target.closest('[data-settle]'),member=e.target.closest('[data-member]');
  if(member){const m=members.find(m=>m.id===member.dataset.member);memberEditing={...m};mf.elements.name.value=m.name;mf.elements.avatar.value='';mf.querySelector('[type=submit]').textContent='保存成员';$('[data-member-cancel]').hidden=false;return;}
  if(busy)return;
  if(edit){const r=records.find(r=>r.id===edit.dataset.edit);editing={...r};selectionTouched=true;for(const [k,v]of Object.entries(r))if(form.elements[k])form.elements[k].value=v;el.querySelectorAll('[name=participant]').forEach(x=>x.checked=r.participants.includes(x.value));form.querySelector('[type=submit]').textContent='保存修改';$('[data-cancel]').hidden=false;$('.expense-status').textContent='';form.scrollIntoView({block:'nearest'});return;}
  if(del){const r=records.find(r=>r.id===del.dataset.delete);if(!r||!confirm(r.kind==='settlement'?'撤销这次还款登记？欠款将重新计入结算。':'从共享账本删除这笔消费？'))return;busy=true;render();try{await cloud.deleteExpense(r);if(editing?.id===r.id)reset();await refresh();$('.expense-status').textContent='已删除，结算结果已更新。';}catch(error){$('.expense-status').textContent=error.message;}finally{busy=false;render();}}
  if(settle){const t={...transfers[+settle.dataset.settle]},snapshot=records.map(r=>r.id+':'+r.version).sort().join('|');if(!t.from||!confirm(`确认 ${name(t.from)} 已实际付给 ${name(t.to)} ${t.currency} ${money(t.amount)}？\n这只登记还款，不会发起真实转账。`))return;
   busy=true;render();try{const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(snapshot+JSON.stringify(t)));const id='settle_'+Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('').slice(0,56);await write({id,version:0,kind:'settlement',amount:t.amount,currency:t.currency,payer:t.from,participants:[t.to],date:today(),category:'其他',method:'刷卡／电子支付',note:'还款'});$('.expense-status').textContent='还款已登记，剩余应付已更新。';}catch(error){$('.expense-status').textContent=error.message+' 请先刷新，确认是否已登记后再操作。';}finally{busy=false;render();}
  }
 });
 function resetMember(){memberEditing=null;memberDraftId=null;mf.reset();mf.querySelector('[type=submit]').textContent='添加成员';$('[data-member-cancel]').hidden=true;}
 $('[data-member-cancel]').onclick=resetMember;
 async function photo(file){
  if(!file)return memberEditing?.avatar||'';
  if(file.size>15*1024*1024)throw Error('请选择15MB以内的照片');
  const url=URL.createObjectURL(file),img=new Image();
  try{img.src=url;await img.decode();const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const context=canvas.getContext('2d');const side=Math.min(img.naturalWidth,img.naturalHeight);context.fillStyle='#ffffff';context.fillRect(0,0,128,128);context.drawImage(img,(img.naturalWidth-side)/2,(img.naturalHeight-side)/2,side,side,0,0,128,128);return canvas.toDataURL('image/jpeg',.78);}finally{URL.revokeObjectURL(url);}
 }
 mf.onsubmit=async e=>{e.preventDefault();const b=mf.querySelector('[type=submit]');if(b.disabled)return;b.disabled=true;$('[data-member-status]').textContent='正在保存…';
  try{const avatar=await photo(mf.elements.avatar.files[0]);await cloud.putMember({id:memberEditing?.id||(memberDraftId??=crypto.randomUUID()),version:memberEditing?.version||0,name:mf.elements.name.value.trim(),avatar});resetMember();await refresh();$('[data-member-status]').textContent=cloud.local?'成员已保存到本机。':'成员已保存并同步。';}
  catch(error){$('[data-member-status]').textContent=error.message||'照片读取失败，请使用 JPG 或 PNG';}finally{b.disabled=false;}
 };
 reset();render();refresh();return{element:el,render,refresh};
};
})();

