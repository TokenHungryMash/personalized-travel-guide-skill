/* No dependencies: embed only actual reviewed captures in an offline phone page. */
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
if (!process.argv[2] || process.argv.includes('--help')) { console.log('node pack_phone_maps.cjs <workbench> [output.html]'); process.exit(process.argv.includes('--help') ? 0 : 2); }
const root = path.resolve(process.argv[2]), dir = path.join(root, 'qa', 'route-capture');
const escape = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
try {
  const plan = JSON.parse(fs.readFileSync(path.join(dir, 'capture-plan.json')));
  const report = JSON.parse(fs.readFileSync(path.join(dir, 'capture-report.json')));
  const rows = new Map(report.captures.map(r => [r.png, r]));
  const local = name => { const p = path.resolve(dir, name); if (path.dirname(p) !== dir) throw Error('非法路径'); return p; };
  const cards = plan.tasks.map(t => {
    const r = rows.get(t.png);
    if (!r || r.status !== 'captured' || r.visual_reviewed !== true || !r.review_note?.trim() || r.observed_state?.status !== 'ready' || r.observed_state?.tiles_loaded !== true || r.observed_state?.labels !== t.stop_numbers.length) throw Error(t.png + ' 尚未完成真实截图和目视检查');
    const bytes = fs.readFileSync(local(t.png));
    if (bytes.subarray(0,8).toString('hex') !== '89504e470d0a1a0a' || bytes.length < 24 || bytes.readUInt32BE(16) < 1400 || bytes.readUInt32BE(20) < 1100) throw Error(t.png + ' 不是合格的大尺寸 PNG');
    if (crypto.createHash('sha256').update(bytes).digest('hex') !== r.sha256) throw Error(t.png + ' 内容已变更');
    const source = fs.readFileSync(local(t.page), 'utf8');
    const match = source.match(/window\.CAPTURE_INPUT=([\s\S]*?);<\/script>/);
    if (!match) throw Error(t.page + ' 缺少地点数据');
    const data = JSON.parse(match[1]);
    if (JSON.stringify(data.stops.map(s => s.number)) !== JSON.stringify(t.stop_numbers)) throw Error(t.page + ' 地点编号不一致');
    return `<section><h2>${escape(t.caption)}</h2><button class="map" aria-label="放大${escape(t.caption)}"><img alt="${escape(t.caption)}：真实道路底图与行程顺序连线" src="data:image/png;base64,${bytes.toString('base64')}"></button><p class="hint">点地图放大，再滑动查看细节。连线表示游览顺序。</p><ol>${data.stops.map(s => `<li value="${Number(s.number)}">${escape(s.name)}</li>`).join('')}</ol></section>`;
  }).join('');
  const html = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>手机离线连线地图</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f2e9;color:#173e35;font:17px/1.6 system-ui,sans-serif}main{max-width:760px;margin:auto;padding:18px}h1{font-size:25px}h2{font-size:21px}section{background:white;padding:14px;border-radius:18px;margin:20px 0}.map{border:0;padding:0;background:none;width:100%;cursor:zoom-in}.map img{display:block;width:100%;border-radius:12px}.hint{font-size:14px;color:#53645f}li{padding:5px 0;overflow-wrap:anywhere}ol{padding-left:32px}dialog{width:100vw;max-width:100vw;height:100dvh;max-height:100dvh;margin:0;padding:0;border:0;background:#f6f2e9}header{display:flex;gap:12px;align-items:center;padding:12px;flex-wrap:wrap}header button{font:inherit;padding:8px 14px}#pan{height:calc(100% - 130px);overflow:auto;touch-action:pan-x pan-y pinch-zoom}#large{display:block;max-width:none;height:auto}input{width:150px}footer{padding:0 12px;font-size:13px}</style>
<main><h1>手机离线连线地图</h1><p>真实道路底图、完整地点名称、行程顺序连线。图片已内嵌，打开后查看地图无需联网。</p>${cards}<p class="hint">OpenFreeMap · © OpenMapTiles · Data from OpenStreetMap。静态图片不提供实时导航，连线不是实际步行或行车路径。</p></main>
<dialog id="viewer"><header><button id="close">关闭大图</button><label>放大 <input id="zoom" type="range" min="100" max="400" step="25" value="100"></label><span id="percent">100%</span></header><div id="pan"><img id="large" alt="放大路线图"></div><footer>拖动滑块放大，左右或上下滑动看全图；也可使用浏览器双指缩放。</footer></dialog>
<script>const viewer=document.getElementById('viewer'),large=document.getElementById('large'),zoom=document.getElementById('zoom'),pan=document.getElementById('pan');function resize(){large.style.width=(pan.clientWidth*Number(zoom.value)/100)+'px';document.getElementById('percent').textContent=zoom.value+'%'}document.querySelectorAll('.map').forEach(button=>button.onclick=()=>{large.src=button.querySelector('img').src;large.alt=button.querySelector('img').alt;zoom.value=100;viewer.showModal();resize();pan.scrollTo(0,0)});zoom.oninput=resize;document.getElementById('close').onclick=()=>viewer.close();window.addEventListener('resize',()=>{if(viewer.open)resize()});</script></html>`;
  fs.writeFileSync(path.resolve(root, process.argv[3] || '手机离线连线地图.html'), html);
  console.log('已打包 ' + plan.tasks.length + ' 张真实地图。输出：' + path.resolve(root, process.argv[3] || '手机离线连线地图.html') + '。仍需手机浏览器实测。');
} catch (error) { console.error('未生成手机交付文件：' + error.message); process.exitCode = 2; }
