/* Optional local member portraits, compatible with the existing name-based ledger. */
(()=>{'use strict';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const validImage=s=>typeof s==='string'&&s.length<=32000&&/^data:image\/jpeg;base64,[A-Za-z0-9+/]+=*$/.test(s);
 const valid=(x,members)=>x===undefined||(x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).length<=30&&Object.entries(x).every(([name,data])=>members.includes(name)&&validImage(data)));
 let ctx,ready=false,memberUndo=null;
 const inactive=(state=ctx?.state)=>{let names=[];try{names=JSON.parse(state?.notes?.ledgerInactiveMembers||'[]')}catch{}return Array.isArray(names)?names.filter(n=>state.members.includes(n)).filter((n,i,a)=>a.indexOf(n)===i):[]};
 const active=(state=ctx?.state)=>{const names=state.members.filter(n=>!inactive(state).includes(n));return names.length?names:[state.members[0]]};
 const referenced=name=>ctx.state.expenses.some(x=>x.payer===name||x.split.includes(name))||(ctx.state.repayments||[]).some(x=>x.from===name||x.to===name)||ctx.memberHasUndo?.(name)||window.MagazineLedger?.referencesMember?.(name);
 function saveMembers(members,hidden,portraits=ctx.state.memberAvatars){const notes={...ctx.state.notes};const kept=hidden.filter(n=>members.includes(n));if(kept.length)notes.ledgerInactiveMembers=JSON.stringify(kept);else delete notes.ledgerInactiveMembers;return ctx.saveMembers({members,notes,memberAvatars:portraits});}
 function restore(name,c=ctx){ctx=c;if(!ctx.state.members.includes(name))return false;return saveMembers([...ctx.state.members],inactive().filter(n=>n!==name));}
 function remove(name){
  const s=ctx.state;if(!s.members.includes(name))return;
  if(active().includes(name)&&active().length===1){status('至少保留一位正在分摊的成员。');return;}
  if(referenced(name)){
   if(!saveMembers([...s.members],[...inactive(),name])){status('保存失败，成员与原账目保持不变。');return;}
   window.MagazineLedger.render(ctx);status(name+'已移出新账分摊，历史账目和结算保留。');return;
  }
  const deleted={name,index:s.members.indexOf(name),photo:s.memberAvatars?.[name],inactive:inactive().includes(name)},portraits={...s.memberAvatars};delete portraits[name];
  if(!saveMembers(s.members.filter(n=>n!==name),inactive().filter(n=>n!==name),portraits)){status('保存失败，成员未删除。');return;}
  memberUndo=deleted;window.MagazineLedger.render(ctx);status(name+'已删除，可撤销。');
 }
 function undoMember(){if(!memberUndo)return;const u=memberUndo,s=ctx.state;if(s.members.includes(u.name)){memberUndo=null;window.MagazineLedger.render(ctx);status('同名成员已存在，未覆盖现有资料。');return;}if(s.members.length>=30){status('成员已满，暂时无法撤销。');return;}const members=[...s.members];members.splice(Math.min(u.index,members.length),0,u.name);const portraits={...s.memberAvatars};if(u.photo)portraits[u.name]=u.photo;if(!saveMembers(members,u.inactive?[...inactive(),u.name]:inactive(),portraits)){status('保存失败，请重试。');return;}memberUndo=null;window.MagazineLedger.render(ctx);status(u.name+'已恢复。');}

 const avatar=(name,state=ctx?.state)=>{const photo=state?.memberAvatars?.[name];return validImage(photo)?`<img class="ledger-avatar" src="${photo}" alt="" width="32" height="32">`:`<span class="ledger-avatar ledger-initial" aria-hidden="true">${esc([...name][0]||'?')}</span>`;};
 const identity=name=>`<span class="ledger-person">${avatar(name)}<span>${esc(name)}</span></span>`;
 const status=text=>{const el=document.querySelector('#member-avatar-status');if(el)el.textContent=text;};
 async function compress(file){
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>10*1024*1024)throw Error('请选择 10MB 以内的 JPG、PNG 或 WebP 照片。');
  const url=URL.createObjectURL(file),img=new Image();
  try{img.src=url;await img.decode();const side=Math.min(img.naturalWidth,img.naturalHeight);if(!side)throw Error();const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const c=canvas.getContext('2d');c.fillStyle='#fff';c.fillRect(0,0,128,128);c.drawImage(img,(img.naturalWidth-side)/2,(img.naturalHeight-side)/2,side,side,0,0,128,128);const data=canvas.toDataURL('image/jpeg',.78);if(!validImage(data))throw Error();return data;}catch(e){throw Error('这张图片无法读取，请换一张 JPG、PNG 或 WebP 照片。');}finally{URL.revokeObjectURL(url);}
 }
 function render(c){ctx=c;const host=document.querySelector('#members-list');
  const live=active(),hidden=inactive(),row=(name,isInactive=false)=>`<div class="ledger-member${isInactive?' is-inactive':''}"><label class="member-photo-picker">${avatar(name)}<span><b>${esc(name)}</b><small>${validImage(c.state.memberAvatars?.[name])?'更换头像':'上传头像'}</small></span><input type="file" accept="image/jpeg,image/png,image/webp" data-member-avatar="${esc(name)}" aria-label="为${esc(name)}上传头像"></label><div class="member-actions">${validImage(c.state.memberAvatars?.[name])?`<button type="button" data-remove-avatar="${esc(name)}" aria-label="移除${esc(name)}的头像">移除头像</button>`:''}${isInactive?`<button type="button" data-restore-member="${esc(name)}">恢复分摊</button>`:''}${!isInactive||!referenced(name)?`<button type="button" data-remove-member="${esc(name)}" ${!isInactive&&live.length===1?'disabled aria-label="至少保留一位分摊成员"':''}>${referenced(name)?'移出分摊':'删除成员'}</button>`:''}</div></div>`;
  host.innerHTML=live.map(n=>row(n)).join('')+(hidden.length?`<details class="inactive-members"><summary>已移出 ${hidden.length} 人 · 保留旧账</summary>${hidden.filter(n=>!live.includes(n)).map(n=>row(n,true)).join('')}</details>`:'')+(memberUndo?'<button type="button" id="undo-member-delete">撤销删除成员</button>':'');
  document.querySelectorAll('[data-member-count]').forEach(n=>n.textContent=live.length);

  if(!document.querySelector('#member-avatar-status'))host.insertAdjacentHTML('afterend','<p id="member-avatar-status" class="small" role="status">未记账成员可删除；有旧账的成员可移出新账分摊，旧账照常结算。</p>');
  if(ready)return;ready=true;
  document.addEventListener('change',async e=>{const input=e.target;if(!input.matches('[data-member-avatar]'))return;const file=input.files[0];if(!file)return;const name=input.dataset.memberAvatar,captured=ctx.state;input.disabled=true;status('正在保存头像…');try{const data=await compress(file);if(ctx.state!==captured||!ctx.state.members.includes(name))return;const next={...ctx.state.memberAvatars,[name]:data};if(!ctx.saveAvatars(next))throw Error('本机空间不足，头像未保存；原头像已保留。');window.MagazineLedger.render(ctx);status(name+'的头像已保存。');}catch(error){status(error.message);}finally{input.disabled=false;input.value='';}});
  document.addEventListener('click',e=>{const del=e.target.closest('[data-remove-member]'),back=e.target.closest('[data-restore-member]');if(del){remove(del.dataset.removeMember);return;}if(back){if(restore(back.dataset.restoreMember)){window.MagazineLedger.render(ctx);status(back.dataset.restoreMember+'已恢复分摊。');}else status('保存失败，请重试。');return;}if(e.target.closest('#undo-member-delete')){undoMember();return;}const button=e.target.closest('[data-remove-avatar]');if(!button)return;const name=button.dataset.removeAvatar,next={...ctx.state.memberAvatars};delete next[name];if(ctx.saveAvatars(next)){window.MagazineLedger.render(ctx);status(name+'的头像已移除。');}else status('移除未保存，请检查本机存储空间。');});
 }
 window.MemberAvatars={valid,avatar,identity,render,active,inactive,restore};
})();
