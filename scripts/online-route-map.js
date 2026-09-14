/* Online basemap; route list remains available without network or WebGL. */
(function(){
'use strict';
var pending, live=new Map();
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function library(){
 if(window.maplibregl)return Promise.resolve(window.maplibregl);
 if(pending)return pending;
 pending=new Promise(function(resolve,reject){
  var css=document.createElement('link');css.rel='stylesheet';css.href='https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css';document.head.appendChild(css);
  var s=document.createElement('script'),t=setTimeout(function(){reject(Error('地图加载超时'))},10000);
  s.src='https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js';s.onload=function(){clearTimeout(t);window.maplibregl?resolve(window.maplibregl):reject(Error('地图组件不可用'))};s.onerror=function(){clearTimeout(t);reject(Error('地图组件未能加载'))};document.head.appendChild(s);
 });return pending;
}
function groupNearby(points,stops,project){
 var pixels=points.map(project),parent=points.map(function(_,i){return i});
 function root(i){while(parent[i]!==i){parent[i]=parent[parent[i]];i=parent[i]}return i}
 pixels.forEach(function(p,i){for(var j=0;j<i;j++){var q=pixels[j];if(Math.abs(p.x-q.x)<144&&Math.abs(p.y-q.y)<38)parent[root(i)]=root(j)}});
 var groups=new Map();points.forEach(function(p,i){var key=root(i);if(!groups.has(key))groups.set(key,{point:p,numbers:[],names:[]});var g=groups.get(key);g.numbers.push(i+1);g.names.push((i+1)+'. '+(stops[i].name||stops[i].placeName||stops[i].place_id||'地点'))});
 return Array.from(groups.values());
}
function markerLabel(group){var name=String(group.names[0]||'地点').replace(/^\d+\.\s*/,''),chars=Array.from(name),short=chars.length>6?chars.slice(0,6).join('')+'…':name;return group.numbers.length>1?group.numbers.length+'站·'+short+'等':group.numbers[0]+'·'+short}
window.TripRouteMaps={mode:'online',groupNearby:groupNearby,markerLabel:markerLabel,render:function(day){
 var stops=Array.isArray(day&&day.stops)?day.stops.filter(function(s){return s&&typeof s==='object'}):[];
 return '<section class="online-trip-map"><div class="online-map-canvas" style="position:relative;height:360px;width:100%;min-width:0;border-radius:12px;overflow:hidden"></div><p class="online-map-note">虚线仅表示行程顺序，不代表实际导航路线。标记显示编号和简短地名；靠近时合并，点击查看完整编号与地点，放大可展开；完整地点名见下方清单。</p><p class="online-map-status" role="status">正在加载地图；下方路线可离线查看。</p><ol style="overflow-wrap:anywhere">'+stops.map(function(s){return '<li>'+esc(s.name||s.placeName||s.place_id)+'</li>'}).join('')+'</ol><script type="application/json" class="online-map-data">'+JSON.stringify(stops).replace(/</g,'\\u003c')+'</script></section>';
}};
function scan(){
 live.forEach(function(map,node){if(!node.isConnected){map.remove();live.delete(node)}});
 document.querySelectorAll('.online-trip-map:not([data-map-started])').forEach(function(node){
  node.dataset.mapStarted='true';var status=node.querySelector('.online-map-status'),stops;
  try{stops=JSON.parse(node.querySelector('.online-map-data').textContent);if(!Array.isArray(stops)||stops.some(function(s){return !s||typeof s!=='object'}))throw Error('Invalid stops')}
  catch(error){if(status)status.textContent='路线数据暂不可用，请查看行程正文。';return}
  var points=stops.map(function(s){return [s.longitude,s.latitude]}),valid=points.length&&points.every(function(p){return p.every(function(v){return typeof v==='number'&&Number.isFinite(v)})&&Math.abs(p[0])<=180&&Math.abs(p[1])<=85});
  if(!valid){status.textContent='坐标待补充，请查看下方路线。';return}
  library().then(function(gl){
   if(!node.isConnected)return;
   var map=new gl.Map({container:node.querySelector('.online-map-canvas'),style:'https://tiles.openfreemap.org/styles/liberty',center:points[0],zoom:12});live.set(node,map);
   map.addControl(new gl.NavigationControl({showCompass:false}),'top-right');
   var timer=setTimeout(function(){if(node.isConnected)status.textContent='底图暂未加载完成，可先查看下方路线。'},10000);
   var resizeObserver=typeof ResizeObserver==='function'?new ResizeObserver(function(){map.resize()}):null;
   if(resizeObserver)resizeObserver.observe(node.querySelector('.online-map-canvas'));
   map.on('remove',function(){clearTimeout(timer);if(resizeObserver)resizeObserver.disconnect()});
   map.on('load',function(){
    clearTimeout(timer);status.textContent='';
    if(points.length>1){map.addSource('itinerary',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:points}}});map.addLayer({id:'itinerary',type:'line',source:'itinerary',paint:{'line-color':'#b46c36','line-width':3,'line-dasharray':[2,2]}})}
    var bounds=new gl.LngLatBounds(points[0],points[0]);points.forEach(function(p){bounds.extend(p)});map.resize();map.fitBounds(bounds,{padding:{top:48,bottom:48,left:80,right:80},maxZoom:15,duration:0});
    var markers=[];
    function redrawMarkers(){
     markers.forEach(function(m){m.remove()});markers=[];
     groupNearby(points,stops,function(p){return map.project(p)}).forEach(function(group){var marker=document.createElement('button');marker.type='button';marker.textContent=markerLabel(group);marker.setAttribute('aria-label',group.names.join('；'));marker.title=group.names.join('；');marker.style.cssText='box-sizing:border-box;background:#28594f;color:white;border:2px solid white;border-radius:20px;width:136px;height:32px;padding:0 6px;overflow:hidden;text-overflow:ellipsis;font:600 13px sans-serif;white-space:nowrap;cursor:pointer';markers.push(new gl.Marker({element:marker}).setLngLat(group.point).setPopup(new gl.Popup().setText(group.names.join('；'))).addTo(map))});
    }
    redrawMarkers();map.on('moveend',redrawMarkers);map.on('resize',redrawMarkers);
   });
   map.on('error',function(){status.textContent='部分地图资源未能加载；下方路线仍可查看。'});
  }).catch(function(){if(node.isConnected)status.textContent='在线地图暂不可用，请查看下方路线。'});
 });
}
new MutationObserver(scan).observe(document.documentElement,{childList:true,subtree:true});
scan();
})();
