/* The same UI runs offline; only persistence changes. No cloud credentials in local HTML. */
(()=>{
 const KEY='bali-shared-ledger-local-v1',listeners=new Set();
 const read=()=>{try{return JSON.parse(localStorage.getItem(KEY))}catch{return null}};
 function load(){
  const saved=read();if(saved)return saved;
  let old=[];try{old=JSON.parse(localStorage.getItem('bali-expenses-v1')||'[]')}catch{}
  if(!Array.isArray(old)||!old.length)return {members:[],expenses:[],checks:[]};
  const members=[{id:'local-owner',name:'我',avatar:'',version:1},{id:'local-companion',name:'同行人',avatar:'',version:1}];
  return {members,checks:[],expenses:old.map(r=>({...r,payer:r.payer==='我'?'local-owner':r.payer==='同行人'?'local-companion':'',participants:members.map(m=>m.id),kind:'expense',version:1,updated_at:r.date+'T00:00:00Z'}))};
 }
 function persist(state){try{localStorage.setItem(KEY,JSON.stringify(state));}catch{throw Error('本机存储空间不足，记录没有保存。请减少头像或释放浏览器空间。')}}
 const refresh=async()=>{const state=load();listeners.forEach(fn=>fn(state));return state;};
 async function put(type,r){const state=load(),list=state[type],index=list.findIndex(x=>x.id===r.id),old=list[index];if((old?.version||0)!==r.version){const error=Error('这条记录已在另一个窗口修改，请刷新后重试');error.status=409;throw error;}if(type==='members'&&index<0&&list.length>=12)throw Error('最多添加12位成员');const next={...r,version:r.version+1,updated_at:new Date().toISOString()};if(index<0)list.push(next);else list[index]=next;persist(state);await refresh();return {ok:true,version:next.version};}
 window.BaliLocalLedger={local:true,refresh,subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn)},putMember:r=>put('members',r),putExpense:r=>put('expenses',r),async deleteExpense(r){const state=load(),old=state.expenses.find(x=>x.id===r.id);if(!old||old.version!==r.version)throw Error('记录已更新，请刷新后重试');state.expenses=state.expenses.filter(x=>x.id!==r.id);persist(state);await refresh();return{ok:true}}};
 window.addEventListener('storage',e=>{if(e.key===KEY)refresh().catch(()=>{});});
})();
