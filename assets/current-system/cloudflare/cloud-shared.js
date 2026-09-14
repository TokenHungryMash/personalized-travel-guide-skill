/* Loaded only by the cloud build. Local HTML keeps its existing local storage behavior. */
(()=>{
  let state = {expenses:[],checks:[]}, pending, listeners = new Set();
  async function request(path,options={}) {
    const isForm=options.body instanceof FormData;
    const response=await fetch(path,{...options,cache:'no-store',credentials:'same-origin',headers:{...(isForm?{}:{'Content-Type':'application/json'}),...options.headers},signal:AbortSignal.timeout(30000)});
    const data=await response.json();
    if(!response.ok){const error=new Error(data.error||'未能同步，请重试');error.status=response.status;if(response.status===401){error.message='登录已到期，请刷新页面重新输入访问码；当前输入未提交。'}throw error;}
    return data;
  }
  async function refresh() {
    if(pending)return pending;
    pending=(async()=>{state=await request('/api/state');listeners.forEach(fn=>fn(state));return state;})().finally(()=>pending=null);
    return pending;
  }
  async function mutate(path,method,data) {
    // Finish an older read before writing so it cannot overwrite the new UI state.
    if(pending)await pending.catch(()=>{});
    try{return await request(path,{method,body:JSON.stringify(data)});}
    catch(error){if(error.status===409)await refresh().catch(()=>{});throw error;}
  }
  window.BaliCloud={refresh,subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn)},
    putExpense:r=>mutate('/api/expenses/'+encodeURIComponent(r.id),'PUT',r),
    putMember:r=>mutate('/api/members/'+encodeURIComponent(r.id),'PUT',r),
    deleteExpense:r=>mutate('/api/expenses/'+encodeURIComponent(r.id),'DELETE',{version:r.version}),
    putCheck:r=>mutate('/api/checks/'+encodeURIComponent(r.id),'PUT',r),
    get state(){return state;}
  };
  window.CloudTicketVault={
    all:key=>request('/api/tickets?placeKey='+encodeURIComponent(key)),
    put:async item=>{
      if(item.cloud)return request('/api/tickets/'+encodeURIComponent(item.id),{method:'PUT',body:JSON.stringify({title:item.title})});
      if(item.dataUrl){const blob=await (await fetch(item.dataUrl)).blob(),form=new FormData();form.append('id',item.id);form.append('placeKey',item.placeKey);form.append('title',item.title);form.append('createdAt',String(item.createdAt));form.append('file',blob,item.fileName||'附件');return request('/api/tickets/file',{method:'POST',body:form});}
      return request('/api/tickets/link',{method:'POST',body:JSON.stringify(item)});
    },
    delete:id=>request('/api/tickets/'+encodeURIComponent(id),{method:'DELETE'})
  };
  function visibleShared(){return !document.hidden && (location.hash==='#booking'||document.querySelector('.trip-mode-panel[data-trip-view="expense"]'))}
  setInterval(()=>{if(visibleShared())refresh().catch(()=>{});},5000);
  document.addEventListener('visibilitychange',()=>{if(visibleShared())refresh().catch(()=>{});});
  window.addEventListener('focus',()=>refresh().catch(()=>{}));
  window.addEventListener('online',()=>refresh().catch(()=>{}));
  document.addEventListener('DOMContentLoaded',()=>{
    const foot=document.querySelector('footer .shell');
    if(foot){const p=document.createElement('p');p.className='cloud-account';p.textContent='共享版 · 账目、预约与收藏附件同步';foot.append(p);}
  });
})();
