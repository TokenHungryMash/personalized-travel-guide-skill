/* Large still-image stage using the same MapLibre/OpenFreeMap as the handbook. */
(function(){
'use strict';
var input=window.CAPTURE_INPUT,host=document.getElementById('map');
window.CAPTURE_STATE={status:'loading'};
document.getElementById('heading').textContent=input.title;
function fail(message){window.CAPTURE_STATE={status:'failed',error:String(message)};document.body.setAttribute('data-capture-state',JSON.stringify(window.CAPTURE_STATE));document.getElementById('heading').textContent='截图未就绪：'+message;}
var timer=setTimeout(function(){fail('底图加载超时；保留日志，不截空白图')},45000);
try{
 var map=new maplibregl.Map({container:host,style:'https://tiles.openfreemap.org/styles/liberty',center:[input.stops[0].longitude,input.stops[0].latitude],zoom:15,interactive:false,attributionControl:false});
 map.on('error',function(e){clearTimeout(timer);fail(e.error&&e.error.message||'地图资源错误')});
 map.on('load',function(){
  if(window.CAPTURE_STATE.status==='failed')return;
  (map.getStyle().layers||[]).forEach(function(layer){
   if(layer.type==='symbol'&&layer.layout&&layer.layout['text-field']){
    map.setLayoutProperty(layer.id,'text-size',/road|street|transportation/.test(layer.id)?24:20);
    map.setLayoutProperty(layer.id,'text-field',['coalesce',['get','name:zh'],['get','name']]);
   }
  });
  var points=input.stops.map(function(s){return[s.longitude,s.latitude]}),bounds=new maplibregl.LngLatBounds(points[0],points[0]);
  points.forEach(function(p){bounds.extend(p)});
  map.fitBounds(bounds,{padding:180,maxZoom:17,duration:0});
  if(!input.overview&&map.getZoom()<15){clearTimeout(timer);fail('局部图跨度过大，需要缩小分组');return;}
  if(points.length>1){map.addSource('route',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:points}}});map.addLayer({id:'route',type:'line',source:'route',paint:{'line-color':'#b87346','line-width':4,'line-dasharray':[2,2]}});}
  map.once('idle',async function(){
   if(window.CAPTURE_STATE.status==='failed')return;
   try{
    await document.fonts.ready;
    if(!map.areTilesLoaded()||!map.isStyleLoaded())throw Error('底图尚未就绪');
    var boxes=[],pixels=points.map(function(p){return map.project(p)}),svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('width','1400');svg.setAttribute('height','974');svg.style.cssText='position:absolute;inset:0;pointer-events:none';host.appendChild(svg);
    input.stops.forEach(function(stop,i){
     var p=pixels[i],label=document.createElement('div');label.className='label';label.textContent=stop.number+' · '+stop.name;label.style.visibility='hidden';host.appendChild(label);
     var w=label.offsetWidth,h=label.offsetHeight,candidates=[];
     for(var y=14;y<host.clientHeight-h-14;y+=18)for(var x=14;x<host.clientWidth-w-14;x+=22){
      var hit=boxes.some(function(b){return !(x+w+10<b.x||b.x+b.w+10<x||y+h+10<b.y||b.y+b.h+10<y)});
      if(hit||pixels.some(function(q){return q.x>x-12&&q.x<x+w+12&&q.y>y-12&&q.y<y+h+12}))continue;
      var ex=Math.max(x,Math.min(p.x,x+w)),ey=Math.max(y,Math.min(p.y,y+h));candidates.push({x:x,y:y,w:w,h:h,ex:ex,ey:ey,d:Math.hypot(ex-p.x,ey-p.y)});
     }
     candidates.sort(function(a,b){return a.d-b.d});if(!candidates.length)throw Error('总览地名无法避让，请调整标签布局后重试；不要自动增加局部图');
     var b=candidates[0];boxes.push(b);label.style.left=b.x+'px';label.style.top=b.y+'px';label.style.visibility='visible';
     var line=document.createElementNS(svg.namespaceURI,'line');[['x1',p.x],['y1',p.y],['x2',b.ex],['y2',b.ey],['stroke','#28594f'],['stroke-width','2']].forEach(function(v){line.setAttribute(v[0],v[1])});svg.appendChild(line);
     var pin=document.createElement('div');pin.className='pin';pin.style.left=p.x+'px';pin.style.top=p.y+'px';host.appendChild(pin);
    });
    await new Promise(function(resolve){requestAnimationFrame(function(){requestAnimationFrame(resolve)})});clearTimeout(timer);
    window.CAPTURE_STATE={status:'ready',zoom:map.getZoom(),labels:boxes.length,tiles_loaded:true,canvas:[map.getCanvas().width,map.getCanvas().height]};
    document.body.setAttribute('data-capture-state',JSON.stringify(window.CAPTURE_STATE));
   }catch(e){clearTimeout(timer);fail(e.message)}
  });
 });
}catch(e){clearTimeout(timer);fail(e.message)}
})();
