/* A clean atlas sheet. Numbered UI markers and place index are rendered outside the raster. */
(async()=>{
 const input=window.ATLAS_INPUT,host=document.getElementById('map');
 const report=(state,detail='')=>{document.body.dataset.ready=state;document.getElementById('status').textContent=detail;};
 const timer=setTimeout(()=>report('failed','底图加载超时'),45000);
 const map=new maplibregl.Map({container:host,style:'https://tiles.openfreemap.org/styles/liberty',interactive:false,attributionControl:false,preserveDrawingBuffer:true});
 map.on('error',e=>{report('failed',e.error?.message||'地图加载失败');clearTimeout(timer)});
 map.on('load',()=>{
  const pts=input.stops.map(s=>[s.longitude,s.latitude]);
  const bounds=new maplibregl.LngLatBounds(pts[0],pts[0]);pts.forEach(p=>bounds.extend(p));
  for(const l of map.getStyle().layers){
   const id=l.id.toLowerCase();
   if(l.type==='background')map.setPaintProperty(l.id,'background-color','#f4f1e8');
   if(l.type==='fill'){
    map.setPaintProperty(l.id,'fill-color',/water/.test(id)?'#c4d9d5':/park|wood|forest|landcover|grass/.test(id)?'#e1e7d7':/building/.test(id)?'#ddd9ce':'#efede3');
    if(l.paint?.['fill-outline-color'])map.setPaintProperty(l.id,'fill-outline-color','#d9d6cb');
   }
   if(l.type==='line'){
    map.setPaintProperty(l.id,'line-color',/water/.test(id)?'#a8c6c1':/boundary/.test(id)?'#b7b8a9':/casing/.test(id)?'#d6cfbe':/motorway|trunk|primary/.test(id)?'#d3c6aa':/rail/.test(id)?'#c1beb1':'#fffef8');
   }
   if(l.type==='symbol'){
    if(/poi|housenumber|airport|shield|oneway/.test(id)){map.setLayoutProperty(l.id,'visibility','none');continue}
    if(l.layout?.['text-field']){
     map.setLayoutProperty(l.id,'text-field',['coalesce',['get','name:en'],['get','name']]);
     map.setLayoutProperty(l.id,'text-size',/road|street/.test(id)?18:/city|town/.test(id)?26:21);
     map.setPaintProperty(l.id,'text-color','#69736a');map.setPaintProperty(l.id,'text-halo-color','#faf8f0');map.setPaintProperty(l.id,'text-halo-width',2);
    }
   }
  }
  map.fitBounds(bounds,{padding:{top:140,bottom:140,left:150,right:150},maxZoom:16.5,duration:0});
  const route=pts;
  map.addSource('journey',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:route}}});
  if(input.key!=='overview'){map.addLayer({id:'journey-halo',type:'line',source:'journey',paint:{'line-color':'#fffdf5','line-width':9,'line-opacity':.9}});
  map.addLayer({id:'journey',type:'line',source:'journey',paint:{'line-color':'#8e5941','line-width':4,'line-dasharray':[2,2]}});
  }
  map.once('idle',()=>{
   if(document.body.dataset.ready==='failed')return;
   const pixels=pts.map(p=>map.project(p)),pins=[];
   pixels.forEach((p,i)=>{
    let chosen={x:p.x,y:p.y};
    for(let radius=0;radius<=480;radius+=35){
     const options=[];
     for(let k=0;k<16;k++){let a=k*Math.PI/8,x=p.x+Math.cos(a)*radius,y=p.y+Math.sin(a)*radius;if(x>75&&x<1325&&y>75&&y<1025&&pins.every(q=>Math.hypot(q.x-x,q.y-y)>=240))options.push({x,y})}
     if(options.length){chosen=options[0];break}
    }
    pins.push({...chosen,px:p.x,py:p.y,id:input.stops[i].place_id,number:input.stops[i].number});
   });
   const svg=document.getElementById('leaders');
   svg.innerHTML=pins.map(p=>`<line x1="${p.px}" y1="${p.py}" x2="${p.x}" y2="${p.y}" stroke="#465a4b" stroke-width="2"/><circle cx="${p.px}" cy="${p.py}" r="5" fill="#263f34"/>`).join('');
   const lat=map.getCenter().lat,metresPerPixel=156543.03392*Math.cos(lat*Math.PI/180)/Math.pow(2,map.getZoom());
   const target=220*metresPerPixel,unit=[50,100,200,500,1000,2000,5000,10000,20000,50000].filter(n=>n<=target).pop()||50;
   document.getElementById('scale').style.width=(unit/metresPerPixel)+'px';document.getElementById('scale-label').textContent=unit>=1000?(unit/1000)+' km':unit+' m';
   document.body.dataset.pins=JSON.stringify(pins.map(p=>({...p,x:p.x/14,y:p.y/11})));
   clearTimeout(timer);report('true');
  });
 });
})();
