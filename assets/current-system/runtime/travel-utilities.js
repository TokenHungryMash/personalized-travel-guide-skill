/* Local-only travel tools. No payment or booking is performed here. */
(()=>{'use strict';
const $=(s,c=document)=>c.querySelector(s),all=(s,c=document)=>Array.from(c.querySelectorAll(s));
const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
const save=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));return true}catch{return false}};
const cloud=window.BaliCloud;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Home shortcuts are text cards. Images remain inside their chapters.
const destinationCards=$('.atlas-destinations');if(destinationCards){const heading=destinationCards.previousElementSibling;if(heading&&heading.classList.contains('atlas-section-title'))heading.remove();destinationCards.remove()}
// The booking list already contains every experience; remove the repeated prose block above it.
$('#move .audit-current-focus')?.remove();
$('#sights .audit-current-focus')?.remove();
$('#shops .current-shopping-plan')?.remove();
// Keep the useful meal overview, but disclose it only when requested.
const diningPlan=$('#food .dining-plan');if(diningPlan&&diningPlan.tagName!=='DETAILS'){
 const fold=document.createElement('details');fold.className=diningPlan.className;
 fold.innerHTML='<summary><b>这次的餐桌</b><span>展开 ＋</span></summary><div class="dining-plan-body"></div>';
 const body=$('.dining-plan-body',fold),intro=$('header>div',diningPlan);if(intro)intro.remove();while(diningPlan.firstChild)body.append(diningPlan.firstChild);diningPlan.replaceWith(fold);
}
// Flights and hotels share one disclosure that can always be opened and closed.
const stay=$('#stay');if(stay&&!$('.travel-info-fold',stay)){
 const shell=$(':scope>.shell',stay),flight=$('#flights',stay);
 if(shell){const heading=$(':scope>.section-heading',shell),fold=document.createElement('details');fold.className='travel-info-fold';
  fold.innerHTML='<summary><span><small>FLIGHT & STAY</small><b>查看航班与住宿</b><em>两段航班 · 两处住宿</em></span><i aria-hidden="true"></i></summary><div class="travel-info-body"></div>';
  const body=$('.travel-info-body',fold);Array.from(shell.children).filter(n=>n!==heading).forEach(n=>body.append(n));if(flight)body.append(flight);shell.append(fold);
 }
}
// Explicit type and three-level priority; preserve previous confirmation state.
all('.audit-reservation').forEach(row=>{
 const title=$('h4',row).textContent,tag=$('.audit-priority',row),select=$('select',row);if(!select)return;
 const category=/Spa|SPA|Bodyworks/i.test(title)?'SPA':/Yoga/i.test(title)?'小狗瑜伽':/冲浪/.test(title)?'冲浪课':/火舞|Kecak/.test(title)?'演出':/FINNS/.test(title)?'海滩俱乐部':/接机|送机|车辆|包车|转场/.test(title)?'交通':'餐厅';
 const level=/Kebun|冲浪/.test(title)?2:/Hujan|Merah|金巴兰/.test(title)?1:0;
 tag.textContent=['必须','建议','随缘'][level];tag.className='audit-priority utility-priority level-'+level;row.dataset.priority=level;
 const type=document.createElement('span');type.className='reservation-type';type.textContent=category;$('h4',row).prepend(type);
 const id=select.dataset.reservationId,key='bali-check:'+id,legacy=(()=>{try{return localStorage.getItem('bali-audit:'+id)}catch{return null}})();
 const label=document.createElement('label');label.className='reservation-check';const check=document.createElement('input');check.type='checkbox';check.checked=read(key,legacy?legacy==='已预约，有凭证':select.value==='已预约，有凭证');
 const text=document.createElement('span');label.append(check,text);select.closest('label').replaceWith(label);
 const sync=()=>{const state=check.checked?'已处理':'待处理';text.textContent=state;row.classList.toggle('reservation-done',check.checked);check.setAttribute('aria-label',title+' '+state)};sync();
 if(cloud){
  check.disabled=true;let version=0,busy=false;
  cloud.subscribe(state=>{const r=state.checks.find(x=>x.id===id);if(r&&!busy){check.checked=r.checked;version=r.version;check.disabled=false;sync()}});
  check.onchange=async()=>{busy=true;check.disabled=true;const old=!check.checked;
   try{const result=await cloud.putCheck({id,checked:check.checked,version});version=result.version;sync();}
   catch(error){check.checked=old;alert(error.message);}
   finally{busy=false;check.disabled=false;cloud.refresh().catch(()=>{});}
  };
 }else check.onchange=()=>{if(!save(key,check.checked)){check.checked=!check.checked;alert('本机保存失败，请检查浏览器存储设置。')}sync()};
});
const sorter=$('[data-reservation-sort][aria-pressed=true]');if(sorter)sorter.click();
const heading=$('.audit-reservations>p');if(heading)heading.textContent='必须：固定项目与交通；建议：重点正餐；随缘：按体力和心情。'+(cloud?'预约勾选两人共享；个人行李清单仍保存在各自手机。':'处理好后打勾，状态保存在本机。');
if(cloud&&heading){const refresh=document.createElement('button');refresh.type='button';refresh.className='cloud-refresh';refresh.textContent='刷新共享状态';heading.after(refresh);refresh.onclick=async()=>{refresh.disabled=true;try{await cloud.refresh();refresh.textContent='已同步'}catch(e){refresh.textContent='连接失败，点击重试'}finally{refresh.disabled=false}};cloud.refresh().catch(()=>{refresh.textContent='尚未连接，点击重试'})}
// Remove photo overlays on these chapter entry buttons, not on venue cards.
all('#move details>summary,#sights .mobile-section-fold>summary').forEach(s=>{
 if(s.closest('#move')&&!s.querySelector('b'))return;
 s.classList.add('utility-readable-fold');
 ['background','background-image','color','min-height','height','padding','display','align-items','justify-content','text-shadow'].forEach((p,i)=>s.style.setProperty(p,['#faf8f1','none','#293e36','76px','auto','18px 20px','flex','center','space-between','none'][i],'important'));
 all('b,h3,strong',s).forEach(n=>{n.style.setProperty('color','#293e36','important');n.style.setProperty('-webkit-text-fill-color','#293e36','important');n.style.setProperty('text-shadow','none','important');n.style.setProperty('position','static','important');n.style.setProperty('margin','0','important')});
});
// Text-only chapter entries: remove the media node and its overlay entirely.
all('.atlas-fold-summary,#sights .mobile-section-fold>summary,#move .mobile-section-fold>summary').forEach(s=>{
 s.classList.remove('has-media');s.classList.add('text-only-entry');
 all('.atlas-fold-media,.atlas-fold-mark',s).forEach(n=>n.remove());
 const props={display:'flex',alignItems:'center',justifyContent:'space-between',minHeight:'80px',height:'auto',padding:'18px 20px',background:'#faf8f1',color:'#293e36',gap:'16px'};
 Object.entries(props).forEach(([k,v])=>s.style.setProperty(k.replace(/[A-Z]/g,m=>'-'+m.toLowerCase()),v,'important'));
 all('.atlas-fold-copy,.atlas-fold-title,.atlas-fold-meta',s).forEach(n=>{['position','transform','text-shadow','opacity'].forEach((k,i)=>n.style.setProperty(k,['static','none','none','1'][i],'important'));n.style.setProperty('color',n.classList.contains('atlas-fold-meta')?'#62675c':'#293e36','important');n.style.setProperty('-webkit-text-fill-color','currentColor','important')});
});
// Practical tips share the same priority language as reservations.
const extraTips=[];
extraTips.forEach(([foldName,title,body])=>{const fold=all('#tips .tips-fold').find(x=>$('summary b',x)?.textContent.trim()===foldName),grid=fold&&$('.tips-grid',fold);if(grid&&!all(':scope>div',grid).some(x=>$('h4',x)?.textContent.trim()===title)){const card=document.createElement('div');card.innerHTML=`<h4>${title}</h4><p>${body}</p>`;grid.append(card)}});
const mustTips=new Set(['饮水与肠胃','海浪、泳池与伤口','寺庙着装与禁区','地面供品','拍摄先询问','仪式与临时封路','Grab 上车确认','从固定时间往前算','猴林与乌鲁瓦图猴子','酒精来源','动物抓咬','保险与就医资料']);
const flexibleTips=new Set(['作息与用餐','何时值得回酒店']);
all('#tips .tips-grid>div').forEach(card=>{const h=$('h4',card);if(!h)return;const level=mustTips.has(h.textContent.trim())?0:flexibleTips.has(h.textContent.trim())?2:1;const badge=document.createElement('span');badge.className='tip-priority tip-level-'+level;badge.textContent=['必须','建议','随缘'][level];h.append(badge);card.dataset.tipPriority=level;});
all('#tips .tips-grid').forEach(grid=>all(':scope>div',grid).sort((a,b)=>Number(a.dataset.tipPriority)-Number(b.dataset.tipPriority)).forEach(card=>grid.append(card)));
const tipsHeading=$('#tips .section-heading');if(tipsHeading){const legend=document.createElement('p');legend.className='tips-priority-legend';legend.textContent='必须：安全、礼仪与固定时间　／　建议：提前留意更省心　／　随缘：按体力与习惯调整';tipsHeading.after(legend);}
// Device speech synthesis. Indonesian entries use an installed Indonesian voice if available.
let speaking=null;const speechStatus=document.createElement('p');speechStatus.className='utility-speech-status';speechStatus.setAttribute('role','status');$('#words .shell')?.prepend(speechStatus);
all('#words .vocab-items>div,#words .phrase-grid>div').forEach(row=>{
 const target=$('b',row);if(!target)return;const value=target.textContent.trim();const button=document.createElement('a');button.href='#';button.className='speech-link';button.textContent=value;button.setAttribute('aria-label','朗读 '+value);button.title='点击朗读，再次点击停止';
 button.onclick=(event)=>{event.preventDefault();if(!('speechSynthesis'in window)){speechStatus.textContent='此浏览器不支持朗读，请使用支持系统语音的浏览器。';return}
 const same=speaking===button;window.speechSynthesis.cancel();if(speaking){speaking.classList.remove('is-speaking');speaking.removeAttribute('aria-current');}speaking=null;if(same)return;
 const group=row.closest('details')?.querySelector('summary')?.textContent||'';const lang=/巴厘岛常见词|地名辨认|印尼语/.test(group)?'id-ID':'en-US';const u=new SpeechSynthesisUtterance(value);u.lang=lang;u.rate=.85;
 const voice=speechSynthesis.getVoices().find(v=>v.lang.toLowerCase().startsWith(lang.slice(0,2)));if(voice)u.voice=voice;
 speechStatus.textContent='使用设备语音朗读；离线可用性取决于已安装语音。';speaking=button;button.classList.add('is-speaking');u.onend=()=>{button.classList.remove('is-speaking');if(speaking===button)speaking=null};u.onerror=()=>{u.onend();speechStatus.textContent='未能播放，请检查设备音量和系统语音设置。'};speechSynthesis.speak(u);
 };target.replaceChildren(button);
});
// Expense ledger: separate totals by currency; never infer transaction amounts.
const sharedLedger=window.createSharedLedger(cloud||window.BaliLocalLedger);const expenseApp=sharedLedger.element;const render=sharedLedger.render;const refreshLedger=sharedLedger.refresh;
function mountExpense(panel){if(!panel)return;const tabs=$('.trip-view-tabs',panel),content=$('.trip-mode-content',panel);if(!tabs||!content)return;let tab=$('.trip-expense-tab',panel);if(!tab){tab=document.createElement('button');tab.id='trip-tab-expense';tab.type='button';tab.className='trip-expense-tab';tab.setAttribute('role','tab');tab.setAttribute('aria-controls','trip-page-expense');tab.dataset.tripView='expense';tab.textContent='记账';tabs.append(tab)}let page=$('#trip-page-expense',panel);if(!page){page=document.createElement('section');page.id='trip-page-expense';page.setAttribute('role','tabpanel');page.setAttribute('aria-labelledby','trip-tab-expense');page.dataset.tripPage='expense';page.hidden=true;page.append(expenseApp);content.append(page)}tab.onclick=()=>{panel.dataset.tripView='expense';all('[data-trip-view]',panel).forEach(b=>{const on=b===tab;b.classList.toggle('is-active',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});all('[data-trip-page]',panel).forEach(p=>p.hidden=p!==page);content.scrollTop=0;render();if(cloud)refreshLedger()};if(panel.dataset.tripView==='expense')tab.click()}
const expenseObserver=new MutationObserver(()=>{const panel=$('.trip-mode-panel');if(panel){const old=$('#trip-page-expense',panel);if(!old)mountExpense(panel)}});expenseObserver.observe(document.body,{childList:true,subtree:true});

// Keep professional outfit guidance beside the matching photo plan in both views.
function mountPhotoOutfit(){const days=window.BALI_ITINERARY||[];all('#route .day').forEach((day,i)=>{const grid=$('.photo-note-grid',day),o=days[i]?.outfit_advice,c=days[i]?.camera_advice;if(grid&&o&&!$('.photo-outfit-note',grid)){const card=document.createElement('div');card.className='photo-outfit-note';card.innerHTML=`<strong>${esc(o.title||'当日穿搭')}</strong><p>${esc(o.description)}</p>`;grid.append(card)}if(grid&&c&&!$('.photo-camera-note',grid)){const card=document.createElement('div');card.className='photo-camera-note';card.innerHTML=`<strong>${esc(c.model)} · 当天设置</strong><p><b>镜头：</b>${esc(c.lens)}</p><p><b>参数：</b>${esc(c.settings)}</p>`;grid.append(card)}});const panel=$('.trip-mode-panel'),card=panel&&$('.trip-photo-card',panel);if(card){const i=all('.trip-mode-day',panel).findIndex(x=>x.classList.contains('is-active')),o=days[i]?.outfit_advice,c=days[i]?.camera_advice,list=$('.trip-shot-list',card);if(o&&list&&!$('.trip-outfit',card)){const article=document.createElement('article');article.className='trip-shot trip-outfit';article.innerHTML=`<b>穿搭</b><div><strong>${esc(o.title||'当日穿搭')}</strong><span>${esc(o.description)}</span></div>`;list.append(article)}if(c&&list&&!$('.trip-camera',card)){const article=document.createElement('article');article.className='trip-shot trip-camera';article.innerHTML=`<b>A7C II</b><div><strong>${esc(c.lens)}</strong><span>${esc(c.settings)}</span></div>`;list.append(article)}const kicker=$('.trip-photo-card header small',card);if(kicker)kicker.textContent='PHOTO NOTES · 摄影、相机和穿搭'}}
mountPhotoOutfit();document.addEventListener('click',e=>{if(e.target.closest('.trip-mode-launch,.trip-mode-day,[data-trip-view="photo"]'))setTimeout(mountPhotoOutfit,0)});
})();
