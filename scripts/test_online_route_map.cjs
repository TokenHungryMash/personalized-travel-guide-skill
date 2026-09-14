// Isolated runtime tests; no browser, network, or destination page access.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'online-route-map.js'), 'utf8');
const nodes = [], maps = [], markers = [];
function node(payload) {
  const status = {textContent: ''};
  return {dataset: {}, isConnected: true, status,
    querySelector(selector) { return selector === '.online-map-status' ? status : selector === '.online-map-data' ? {textContent: payload} : {}; }};
}
const context = {
  window: {maplibregl: {
    Map: class { constructor() { this.events = {}; maps.push(this); }
      on(name, fn) { this.events[name] = fn; } resize() {} fitBounds() {} addControl() {}
      project(p) {return {x:p[0]*100,y:p[1]*100};}
      addSource() {} addLayer() {} remove() { this.events.remove?.(); } },
    Marker: class { constructor(options) { markers.push(options.element); }
      setLngLat(p) { this.point = p; return this; } setPopup() { return this; } addTo() { return this; } remove() {} },
    NavigationControl: class {},
    Popup: class { setText() { return this; } },
    LngLatBounds: class { extend() {} }
  }},
  document: {documentElement: {}, querySelectorAll() { return nodes.filter(n => !n.dataset.mapStarted); },
    createElement() { return {setAttribute() {}, style: {}}; }},
  MutationObserver: class { constructor(fn) { context.scan = fn; } observe() {} },
  setTimeout() { return 1; }, clearTimeout() {},
};
vm.runInNewContext(source, context);
const render = context.window.TripRouteMaps.render;
assert.ok(render({stops: null}).includes('<ol'));
assert.ok(render({stops: [null, {name: '</script><b>place</b>'}]}).includes('&lt;/script&gt;'));
const html = render({stops: [{name: '</script>'}]});
const embedded = html.match(/class="online-map-data">(.*?)<\/script>/)[1];
assert.equal(JSON.parse(embedded)[0].name, '</script>');
nodes.push(node('{broken'), node(JSON.stringify([
  {name: 'Start', latitude: 33, longitude: 130},
  {name: 'Other', latitude: 34, longitude: 131},
  {name: 'Return', latitude: 33, longitude: 130}
])));
context.scan();
Promise.resolve().then(() => {
  assert.ok(nodes[0].status.textContent.includes('路线数据暂不可用'));
  assert.equal(maps.length, 1, 'one malformed map must not abort following maps');
  maps[0].events.load();
  assert.equal(markers.length, 2, 'same coordinates must share one marker');
  assert.equal(markers[0].textContent, '2站·Start等');
  assert.equal(markers[1].textContent, '2·Other');
  const group = context.window.TripRouteMaps.groupNearby;
  const label=context.window.TripRouteMaps.markerLabel;
  assert.equal(label({numbers:[1],names:['1. 浅草寺']}),'1·浅草寺');
  assert.equal(label({numbers:[1,2],names:['1. 浅草寺','2. 仲见世']}),'2站·浅草寺等');
  assert.ok(label({numbers:[3],names:['3. 很长很长很长很长的地点名称']}).includes('…'));
  assert.equal(group([[0,0],[1,0]], [{name:'A'},{name:'B'}], p=>({x:p[0]*100,y:0})).length,1,'name pills must not overlap horizontally');
  const pts=[[0,0],[0.2,0.1],[3,3]], stops=pts.map((_,i)=>({name:'Place '+i}));
  const overview=group(pts,stops,p=>({x:p[0]*100,y:p[1]*100}));
  assert.equal(overview.length,2,'nearby, non-identical stops must not overlap');
  assert.deepEqual(Array.from(overview[0].numbers),[1,2]);
  assert.equal(group(pts,stops,p=>({x:p[0]*1000,y:p[1]*1000})).length,3,'zoom separates nearby markers');
  assert.equal(group([[0,0],[0,0]],stops,p=>({x:p[0],y:p[1]})).length,1,'coincident points stay grouped');
  assert.equal(pts[1][0],0.2,'grouping must not change geographic coordinates');
  console.log('PASS map escaping, data isolation, collision grouping and zoom expansion');
}).catch(error => { console.error(error); process.exitCode = 1; });
