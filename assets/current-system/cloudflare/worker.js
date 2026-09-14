
const json = (data, status = 200) => new Response(JSON.stringify(data), {status, headers: {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store'}});
async function body(request, limit=4096) {
  if (!request.headers.get('Content-Type')?.startsWith('application/json')) throw new Error('请使用 JSON 格式');
  const reader = request.body?.getReader();
  if (!reader) throw new Error('请求为空');
  let size = 0, chunks = [];
  for (;;) { const {done, value} = await reader.read(); if(done) break; size += value.length; if(size > limit) {await reader.cancel(); throw new Error('内容过长');} chunks.push(value); }
  const bytes = new Uint8Array(size); let offset = 0;
  for(const chunk of chunks) {bytes.set(chunk, offset); offset += chunk.length;}
  const value = JSON.parse(new TextDecoder().decode(bytes));
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('请求格式不正确');
  return value;
}
function validateExpense(r) {
  const lists = {currency:['KRW','IDR','JPY','CNY','USD','HKD'], category:['餐饮','交通','住宿','门票与体验','购物','其他'], method:['刷卡／电子支付','现金']};
  for(const [key, allowed] of Object.entries(lists)) if(!allowed.includes(r[key])) throw new Error('请选择有效的'+key);
  if(typeof r.amount !== 'number' || !Number.isFinite(r.amount) || r.amount <= 0 || r.amount > 1e10 || Math.abs(r.amount * 100 - Math.round(r.amount * 100)) > .001) throw new Error('金额必须大于零，最多两位小数');
  if(typeof r.date !== 'string' || !/^202\d-\d{2}-\d{2}$/.test(r.date) || !Number.isFinite(Date.parse(r.date)) || new Date(r.date).toISOString().slice(0,10) !== r.date) throw new Error('日期不正确');
  if(typeof r.note !== 'string' || r.note.length > 120) throw new Error('备注最多120字');
  return Math.round(r.amount * 100);
}
const ticketId=/^[a-zA-Z0-9_-]{8,64}$/;
function cleanText(value,max,label){if(typeof value!=='string'||!value.trim()||value.trim().length>max)throw new Error(label+'不正确');return value.trim()}
function cleanUrl(value){const text=cleanText(value,2048,'链接');let url;try{url=new URL(text)}catch{throw new Error('链接不正确')}if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw new Error('链接不正确');return url.href}
function safeFileName(value){return String(value||'附件').replace(/[\r\n"\\]/g,'_').slice(0,160)||'附件'}
async function api(request, env, path) {
  if(path === '/api/state' && request.method === 'GET') {
    const results = await env.DB.batch([
      env.DB.prepare('SELECT id, amount_minor, currency, date, category, payer, method, note, version, updated_at,split_json,kind FROM expenses WHERE deleted=0 ORDER BY date DESC'),
      env.DB.prepare('SELECT id, checked, version FROM checks'),
      env.DB.prepare('SELECT id,name,avatar,version FROM members ORDER BY rowid')
    ]);
    return json({expenses:results[0].results.map(({amount_minor,split_json,...r})=>({...r,amount:amount_minor/100,participants:JSON.parse(split_json)})), checks:results[1].results.map(r=>({...r,checked:!!r.checked})),members:results[2].results});
  }
  if(path==='/api/tickets'&&request.method==='GET'){
    const placeKey=new URL(request.url).searchParams.get('placeKey');
    if(!placeKey||placeKey.length>200)return json({error:'地点不正确'},400);
    const rows=await env.DB.prepare('SELECT id,place_key,title,url,file_name,content_type,size,created_at FROM tickets WHERE place_key=? ORDER BY created_at DESC').bind(placeKey).all();
    return json(rows.results.map(r=>({id:r.id,placeKey:r.place_key,title:r.title,url:r.url||undefined,fileName:r.file_name||undefined,dataUrl:r.file_name?'/api/tickets/'+encodeURIComponent(r.id)+'/content':undefined,contentType:r.content_type||undefined,size:r.size||undefined,createdAt:r.created_at,cloud:true})));
  }
  if(path==='/api/tickets/link'&&request.method==='POST'){
    const r=await body(request,8192),id=cleanText(r.id,64,'编号'),placeKey=cleanText(r.placeKey,200,'地点'),title=cleanText(r.title,60,'按钮名称'),url=cleanUrl(r.url),createdAt=Number(r.createdAt)||Date.now();
    if(!ticketId.test(id))return json({error:'编号不正确'},400);
    await env.DB.prepare('INSERT INTO tickets(id,place_key,title,url,created_at) VALUES(?,?,?,?,?)').bind(id,placeKey,title,url,createdAt).run();
    return json({ok:true});
  }
  if(path==='/api/tickets/file'&&request.method==='POST'){
    const declared=Number(request.headers.get('Content-Length')||0);if(declared>21*1024*1024)return json({error:'文件请控制在20MB以内'},413);
    const form=await request.formData(),id=cleanText(form.get('id'),64,'编号'),placeKey=cleanText(form.get('placeKey'),200,'地点'),title=cleanText(form.get('title'),60,'按钮名称'),file=form.get('file');
    if(!ticketId.test(id)||!(file instanceof File))return json({error:'附件不正确'},400);
    if(file.size>20*1024*1024)return json({error:'文件请控制在20MB以内'},413);
    if(!(file.type==='application/pdf'||file.type.startsWith('image/')))return json({error:'仅支持 PDF 或图片'},400);
    const fileName=safeFileName(file.name),objectKey='tickets/'+id+'/'+fileName,createdAt=Number(form.get('createdAt'))||Date.now();
    await env.UPLOADS.put(objectKey,file.stream(),{metadata:{contentType:file.type||'application/octet-stream',fileName}});
    try{await env.DB.prepare('INSERT INTO tickets(id,place_key,title,file_name,object_key,content_type,size,created_at) VALUES(?,?,?,?,?,?,?,?)').bind(id,placeKey,title,fileName,objectKey,file.type,file.size,createdAt).run()}catch(error){await env.UPLOADS.delete(objectKey);throw error}
    return json({ok:true});
  }
  const ticketContent=path.match(/^\/api\/tickets\/([a-zA-Z0-9_-]{8,64})\/content$/);
  if(ticketContent&&request.method==='GET'){
    const row=await env.DB.prepare('SELECT object_key,file_name,content_type FROM tickets WHERE id=?').bind(ticketContent[1]).first();if(!row?.object_key)return json({error:'附件不存在'},404);
    const object=await env.UPLOADS.getWithMetadata(row.object_key,{type:'stream'});if(!object.value)return json({error:'附件正在同步，请稍后重试'},503);
    const headers=new Headers({'Content-Type':object.metadata?.contentType||row.content_type||'application/octet-stream','Content-Disposition':'inline','Cache-Control':'private, no-store'});return new Response(object.value,{headers});
  }
  const ticketMatch=path.match(/^\/api\/tickets\/([a-zA-Z0-9_-]{8,64})$/);
  if(ticketMatch&&request.method==='PUT'){
    const r=await body(request,4096),title=cleanText(r.title,60,'按钮名称'),result=await env.DB.prepare('UPDATE tickets SET title=? WHERE id=?').bind(title,ticketMatch[1]).run();return result.meta.changes?json({ok:true}):json({error:'收藏不存在'},404);
  }
  if(ticketMatch&&request.method==='DELETE'){
    const row=await env.DB.prepare('SELECT object_key FROM tickets WHERE id=?').bind(ticketMatch[1]).first();if(!row)return json({error:'收藏不存在'},404);
    await env.DB.prepare('DELETE FROM tickets WHERE id=?').bind(ticketMatch[1]).run();if(row.object_key)await env.UPLOADS.delete(row.object_key);return json({ok:true});
  }
  const memberMatch=path.match(/^\/api\/members\/([a-zA-Z0-9_-]{8,64})$/);
  if(memberMatch&&request.method==='PUT'){
    const r=await body(request,40000);
    if(typeof r.name!=='string'||!r.name.trim()||r.name.trim().length>20||!Number.isInteger(r.version)||r.version<0) return json({error:'请填写20字以内的姓名'},400);
    if(typeof r.avatar!=='string'||r.avatar.length>32000||(r.avatar&&!/^data:image\/jpeg;base64,[A-Za-z0-9+/]+=*$/.test(r.avatar)))return json({error:'头像格式不正确，请重新选择照片'},400);
    const result=r.version===0?await env.DB.prepare('INSERT OR IGNORE INTO members(id,name,avatar) SELECT ?,?,? WHERE (SELECT count(*) FROM members)<12').bind(memberMatch[1],r.name.trim(),r.avatar).run():await env.DB.prepare('UPDATE members SET name=?,avatar=?,version=version+1 WHERE id=? AND version=?').bind(r.name.trim(),r.avatar,memberMatch[1],r.version).run();
    return result.meta.changes===1?json({ok:true,version:r.version+1}):json({error:'成员已更新或已达到12人上限，请刷新后重试'},409);
  }
  const expenseMatch = path.match(/^\/api\/expenses\/([a-zA-Z0-9_-]{8,64})$/);
  const checkMatch = path.match(/^\/api\/checks\/([a-zA-Z0-9_-]{1,100})$/);
  if((expenseMatch && ['PUT','DELETE'].includes(request.method)) || (checkMatch && request.method === 'PUT')) {
    const r = await body(request);
    if(!Number.isInteger(r.version) || r.version < 0) return json({error:'缺少记录版本，请刷新后重试'},400);
    let result;
    if(expenseMatch) {
      const id = expenseMatch[1], now = new Date().toISOString();
      if(request.method === 'DELETE') {
        result = await env.DB.prepare('UPDATE expenses SET deleted=1, version=version+1, updated_at=? WHERE id=? AND version=? AND deleted=0').bind(now,id,r.version).run();
      } else {
        const amount = validateExpense(r);
        const members=await env.DB.prepare('SELECT id FROM members').all(),ids=new Set(members.results.map(m=>m.id));
        if(!ids.has(r.payer)||!Array.isArray(r.participants)||!r.participants.length||r.participants.length>12||new Set(r.participants).size!==r.participants.length||r.participants.some(id=>!ids.has(id)))return json({error:'请选择付款人及至少一位分摊成员'},400);
        if(!['expense','settlement'].includes(r.kind)||(r.kind==='settlement'&&(r.participants.length!==1||r.participants[0]===r.payer)))return json({error:'还款双方不正确'},400);
        const split=JSON.stringify(r.participants);
        if(r.version === 0) result = await env.DB.prepare('INSERT OR IGNORE INTO expenses (id,amount_minor,currency,date,category,payer,method,note,updated_at,split_json,kind) VALUES (?,?,?,?,?,?,?,?,?,?,?)').bind(id,amount,r.currency,r.date,r.category,r.payer,r.method,r.note,now,split,r.kind).run();
        else result = await env.DB.prepare('UPDATE expenses SET amount_minor=?,currency=?,date=?,category=?,payer=?,method=?,note=?,updated_at=?,split_json=?,kind=?,version=version+1 WHERE id=? AND version=? AND deleted=0').bind(amount,r.currency,r.date,r.category,r.payer,r.method,r.note,now,split,r.kind,id,r.version).run();
      }
    } else {
      if(typeof r.checked !== 'boolean') return json({error:'勾选状态不正确'},400);
      result = await env.DB.prepare('UPDATE checks SET checked=?,version=version+1 WHERE id=? AND version=?').bind(r.checked?1:0,checkMatch[1],r.version).run();
    }
    if(result.meta.changes !== 1) return json({error:'同行人刚修改了这条记录，已保留你的输入。请查看最新内容后再决定。'},409);
    return json({ok:true,version:r.version+1});
  }
  return json({error:'接口不存在'},404);
}
async function digest(value){return new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))}
function sameBytes(actual,expected){let different=actual.length^expected.length;for(let i=0;i<Math.max(actual.length,expected.length);i++)different|=(actual[i%actual.length]||0)^(expected[i%expected.length]||0);return different===0}
async function sessionToken(env){
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.ACCESS_CODE),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const bytes=new Uint8Array(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode('travel-guide-session-v1')));
  return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
}
async function accessAllowed(request,env){
  if(env.ACCESS_MODE!=='code')return true;
  if(!env.ACCESS_CODE)return false;
  const cookie=(request.headers.get('Cookie')||'').split(';').map(x=>x.trim()).find(x=>x.startsWith('guide_access='));
  if(!cookie)return false;
  const [actual,expected]=await Promise.all([digest(cookie.slice('guide_access='.length)),digest(await sessionToken(env))]);
  return sameBytes(actual,expected);
}
function loginPage(message='',status=200){
  const notice=message?`<p class="error">${message}</p>`:'';
  const html=`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>旅行手册 · 访问验证</title><style>*{box-sizing:border-box}body{margin:0;min-height:100svh;display:grid;place-items:center;padding:24px;background:#f3efe5;color:#173f36;font-family:system-ui,"Microsoft YaHei",sans-serif}.card{width:min(100%,420px);padding:34px 26px;background:#fffdf8;border:1px solid #d8d0bf;border-radius:22px;box-shadow:0 18px 55px #173f3620}small{letter-spacing:.16em;color:#a45f46}h1{margin:10px 0 8px;font-size:30px}p{color:#61716b;line-height:1.7}.error{color:#a33b2e}label{display:block;margin:24px 0 8px;font-weight:700}input{width:100%;height:50px;padding:0 14px;border:1px solid #aebdb6;border-radius:12px;font-size:17px;background:white}button{width:100%;height:50px;margin-top:14px;border:0;border-radius:12px;background:#1f5c50;color:white;font-size:16px;font-weight:700}</style></head><body><main class="card"><small>PRIVATE TRAVEL GUIDE</small><h1>同行访问</h1><p>输入分享者提供的访问码，即可打开旅行手册。</p>${notice}<form method="post" action="/__access"><label for="code">访问码</label><input id="code" name="code" type="password" autocomplete="current-password" required autofocus><button type="submit">打开旅行手册</button></form></main></body></html>`;
  return new Response(html,{status,headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'private, no-store'}});
}
async function login(request,env){
  const declared=Number(request.headers.get('Content-Length')||0);if(declared>2048)return loginPage('请求内容过长，请重试。',400);
  const form=await request.formData(),code=String(form.get('code')||'');
  const [actual,expected]=await Promise.all([digest(code),digest(env.ACCESS_CODE||'')]);
  if(!env.ACCESS_CODE||!sameBytes(actual,expected))return loginPage('访问码不正确，请重新输入。',401);
  return new Response(null,{status:303,headers:{Location:'/', 'Set-Cookie':`guide_access=${await sessionToken(env)}; Path=/; Max-Age=2592000; HttpOnly; Secure; SameSite=Lax`, 'Cache-Control':'private, no-store'}});
}
function accessDenied(path){return path.startsWith('/api/')?json({error:'需要有效访问码'},401):loginPage()}
async function route(request, env) {
  const url = new URL(request.url), path = url.pathname;
  if(env.ACCESS_MODE==='code'&&path==='/__access'&&request.method==='POST')return login(request,env);
  if(!await accessAllowed(request,env))return accessDenied(path);
  if(request.method !== 'GET' && request.method !== 'HEAD') {
    if(request.headers.get('Origin') !== url.origin) return json({error:'请从手册页面操作'},403);
  }
  if(path.startsWith('/api/')) return api(request,env,path);
  if(!['GET','HEAD'].includes(request.method)) return new Response('Method not allowed',{status:405});
  return env.ASSETS.fetch(request);
}
export default {
  async fetch(request,env) {
    let response;
    try {response = await route(request,env);} catch(error) {
      const isInput = error instanceof SyntaxError || /请求|格式|内容过长|请选择|金额|日期|备注/.test(error.message);
      if(!isInput) console.error(JSON.stringify({event:'request_failed',path:new URL(request.url).pathname,message:error.message}));
      response = json({error:isInput?error.message:'暂时未能连接账本，请稍后重试；输入尚未提交。'},isInput?400:503);
    }
    response = new Response(response.body,response);
    response.headers.set('Cache-Control','private, no-store');
    response.headers.set('X-Content-Type-Options','nosniff');
    response.headers.set('X-Frame-Options',new URL(request.url).pathname.match(/^\/api\/tickets\/[a-zA-Z0-9_-]{8,64}\/content$/)?'SAMEORIGIN':'DENY');
    response.headers.set('Referrer-Policy','no-referrer');
    response.headers.set('X-Robots-Tag','noindex, nofollow, noarchive');
    return response;
  }
};
