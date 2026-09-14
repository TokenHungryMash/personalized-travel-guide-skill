const fs=require('fs'),path=require('path');
const [input,output,tileRoot,vectorFile]=process.argv.slice(2);
if(!input||!output||!tileRoot)throw Error('Usage: node build_system_routes.cjs days.json output-directory tiles-directory [vector.json]');
const data=JSON.parse(fs.readFileSync(input,'utf8')),days=Array.isArray(data)?data:data.days;
const source=vectorFile?JSON.parse(fs.readFileSync(vectorFile,'utf8')):{ways:[]};
const outputs=[path.join(output,'media/routes')];
function tile(z,x,y){const file=path.join(tileRoot,String(z),String(x),y+'.png');if(!fs.existsSync(file))throw Error('Missing licensed basemap tile: '+file);const bytes=fs.readFileSync(file);if(bytes.subarray(0,8).toString('hex')!=='89504e470d0a1a0a')throw Error('Not a PNG tile: '+file);return 'data:image/png;base64,'+bytes.toString('base64');}
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const weight = s => Array.from(s).reduce((n,c) => n + (/[^\x00-\xff]/.test(c) ? 2 : 1), 0);
function wrap(name, limit=16) {
  const lines=[]; let line='', used=0;
  for (const c of Array.from(name)) { const w=/[^\x00-\xff]/.test(c)?2:1; if (line && used+w>limit*2) { lines.push(line); line=c; used=w; } else { line+=c; used+=w; } }
  if (line) lines.push(line); return lines;
}
function segmentHitsRect(a,b,r,pad=8) {
  const minx=Math.min(a[0],b[0]), maxx=Math.max(a[0],b[0]), miny=Math.min(a[1],b[1]), maxy=Math.max(a[1],b[1]);
  return !(maxx<r.x-pad || minx>r.x+r.w+pad || maxy<r.y-pad || miny>r.y+r.h+pad);
}
function resolvePoints(day) {return day.stops.map((s,i)=>{if(s.latitude==null||s.longitude==null||!Number.isFinite(+s.latitude)||!Number.isFinite(+s.longitude)||Math.abs(+s.latitude)>85||Math.abs(+s.longitude)>180)throw Error('Missing/invalid verified coordinates for '+s.name);if(s.routeOrder!=null&&s.routeOrder!==i+1)throw Error('routeOrder disagrees with itinerary array; do not reorder');return{name:s.placeName||s.name,index:(s.stopIndex??i+1)-1,p:[+s.longitude,+s.latitude]};});}
function projectPoints(points, schematic) {
  if (schematic) return points.map((p,i)=>({...p,actual:[i%2?405:195,105+i*420/Math.max(1,points.length-1)]}));
  const located=points.filter(p=>p.p);
  const world=(p,z)=>{const n=256*Math.pow(2,z),lat=Math.max(-85.0511,Math.min(85.0511,p[1]))*Math.PI/180;return[(p[0]+180)/360*n,(1-Math.log(Math.tan(lat)+1/Math.cos(lat))/Math.PI)/2*n]};
  let zoom=16,pixels;
  for(;zoom>8;zoom--){pixels=located.map(p=>world(p.p,zoom));const sx=Math.max(...pixels.map(p=>p[0]))-Math.min(...pixels.map(p=>p[0])),sy=Math.max(...pixels.map(p=>p[1]))-Math.min(...pixels.map(p=>p[1]));if(sx<=390&&sy<=455)break;}
  pixels=located.map(p=>world(p.p,zoom));const cx=(Math.min(...pixels.map(p=>p[0]))+Math.max(...pixels.map(p=>p[0])))/2,cy=(Math.min(...pixels.map(p=>p[1]))+Math.max(...pixels.map(p=>p[1])))/2;
  const project=p=>{const q=world(p,zoom);return[300+q[0]-cx,315+q[1]-cy]};
  let tiles='';const minX=Math.floor((cx-330)/256),maxX=Math.floor((cx+330)/256),minY=Math.floor((cy-345)/256),maxY=Math.floor((cy+345)/256),count=Math.pow(2,zoom);
  for(let tx=minX;tx<=maxX;tx++)for(let ty=minY;ty<=maxY;ty++){const x=300+tx*256-cx,y=315+ty*256-cy;tiles+='<image href="'+tile(zoom,((tx%count+count)%count),ty)+'" x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="256" height="256" opacity=".86"/>';}
  project.tiles=tiles;
  const projected=points.filter(p=>p.p).map(p=>({...p,actual:project(p.p)}));
  const seen=new Map();
  projected.forEach(p=>{const key=p.p.map(v=>v.toFixed(5)).join(',');const count=seen.get(key)||0;seen.set(key,count+1);p.display=[p.actual[0]+count*15,p.actual[1]+count*11];});
  return {points:projected,project,tiles};
}
function basemap(project) {
  let land='',roads='',buildings=''; const seen=new Set();
  source.ways.forEach(w=>{const ps=w.p.map(project);if(!ps.some(p=>p[0]>-30&&p[0]<630&&p[1]>-30&&p[1]<650))return;const d=ps.map((p,i)=>(i?'L':'M')+p.map(v=>v.toFixed(1)).join(',')).join('');if(seen.has(d))return;seen.add(d);const t=w.t;
    if(t.building){buildings+='<path d="'+d+'Z" fill="#dedbd2"/>';return;}
    if(t.landuse||t.natural){const fill=t.natural==='water'?'#cee4e9':/forest|wood|grass|farmland|meadow|scrub/.test((t.landuse||'')+' '+(t.natural||''))?'#d3e8bd':'#ebe8df';land+='<path d="'+d+'Z" fill="'+fill+'"/>';}
    if(t.waterway)land+='<path d="'+d+'" fill="none" stroke="#b9dbe5" stroke-width="6"/>';
    if(t.highway){const major=/primary|secondary|tertiary/.test(t.highway);roads+='<path d="'+d+'" fill="none" stroke="'+(major?'#c8c4b9':'#d6d3ca')+'" stroke-width="'+(major?10:5)+'"/><path d="'+d+'" fill="none" stroke="#fffdf7" stroke-width="'+(major?6:2.5)+'"/>';}
  }); return (project.tiles||'')+land+buildings+roads;
}
function routeLayer(points) {
  let out='';
  for(let i=0;i<points.length-1;i++){const a=points[i].display||points[i].actual,b=points[i+1].display||points[i+1].actual,mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2,angle=Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI,d='M'+a.join(',')+' C'+mx+','+a[1]+' '+mx+','+b[1]+' '+b.join(',');out+='<path d="'+d+'" class="route-under"/><path d="'+d+'" class="route-main"/><path d="M-4,-3 L4,0 L-4,3 Z" class="route-arrow" transform="translate('+mx+' '+my+') rotate('+angle+')"/>';}
  return out;
}
function labelLayer(points) {
  const placed=[], routeSegments=points.slice(0,-1).map((p,i)=>[p.display||p.actual,points[i+1].display||points[i+1].actual]); let labels='';
  points.forEach(p=>{const rows=wrap(p.name),width=rows.length>1?270:Math.min(370,Math.max(150,weight(p.name)*9+65)),height=Math.max(48,22+rows.length*21),pin=p.display||p.actual;let best=null;
    for(const dy of [-72,24,-140,92,-206,158,216])for(const dx of [-width/2,20,-width-20]){const x=Math.max(10,Math.min(590-width,pin[0]+dx)),y=Math.max(12,Math.min(625-height,pin[1]+dy)),r={x,y,w:width,h:height};const overlap=placed.reduce((sum,q)=>sum+Math.max(0,Math.min(x+width+9,q.x+q.w)-Math.max(x-9,q.x))*Math.max(0,Math.min(y+height+9,q.y+q.h)-Math.max(y-9,q.y)),0),routePenalty=routeSegments.reduce((n,s)=>n+(segmentHitsRect(s[0],s[1],r)?1:0),0),score=overlap*100+routePenalty*180+Math.hypot(x+width/2-pin[0],y+height/2-pin[1]);if(!best||score<best.score)best={...r,score};}
    placed.push(best);const{x,y}=best,cy=y+height/2;labels+='<path d="M'+pin.join(',')+' L'+(x+width/2)+','+cy+'" class="leader"/><rect x="'+x+'" y="'+y+'" width="'+width+'" height="'+height+'" rx="13" class="label-bg"/><circle cx="'+(x+24)+'" cy="'+cy+'" r="18" class="label-number-bg"/><text x="'+(x+24)+'" y="'+(cy+6)+'" class="label-number">'+(p.index+1)+'</text>'+rows.map((row,i)=>'<text x="'+(x+50)+'" y="'+(y+(rows.length===1?29:23+i*21))+'" class="label-name">'+esc(row)+'</text>').join('');
  });
  const markers=points.map(p=>{const q=p.display||p.actual;return '<g transform="translate('+q.join(' ')+')"><circle r="13" class="map-marker"/><text y="5" class="map-marker-text">'+(p.index+1)+'</text></g>';}).join('');
  return labels+markers;
}
outputs.forEach(x=>fs.mkdirSync(x,{recursive:true})); const metadata=[];
const panels=[];days.forEach((day,dayIndex)=>{if(!day.stops?.length)throw Error("Day has no stops");const stops=day.stops.map((s,i)=>({...s,stopIndex:s.stopIndex??i+1}));for(let start=0;start<stops.length;start+=4){const slice=stops.slice(start,start+5);if(start&&slice.length===1)break;panels.push({...day,stops:slice.map((s,i)=>({...s,routeOrder:i+1})),dayIndex});}});
panels.forEach((day,di)=>{const raw=resolvePoints(day),schematic=false,projection=projectPoints(raw,schematic),points=schematic?projection:projection.points,map=schematic?'':basemap(projection.project),defs='<defs><clipPath id="map-clip"><rect width="600" height="650" rx="20"/></clipPath><style>.route-under{fill:none;stroke:#fff;stroke-width:8;stroke-linecap:round}.route-main{fill:none;stroke:#665bd5;stroke-width:4;stroke-linecap:round}.route-arrow{fill:#665bd5}.leader{stroke:#687f77;stroke-width:1.2}.label-bg{fill:#fffffff2;stroke:#aebbb5;stroke-width:1}.label-number-bg{fill:#665bd5}.label-number{fill:#fff;text-anchor:middle;font:700 15px Arial}.label-name{fill:#243730;font:500 17px Arial,"Microsoft YaHei",sans-serif}.map-marker{fill:#665bd5;stroke:#fff;stroke-width:3}.map-marker-text{fill:#fff;text-anchor:middle;font:700 12px Arial}</style></defs>',note=schematic?'跨城航段按行程顺序显示':'© OpenStreetMap contributors · 非逐路口导航',svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 690" role="img" aria-label="'+esc(day.theme)+'路线图">'+defs+'<rect width="600" height="690" fill="#f7f5ef"/><g clip-path="url(#map-clip)">'+map+'<rect width="600" height="650" fill="#fff" opacity=".04"/>'+routeLayer(points)+labelLayer(points)+'</g><rect y="650" width="600" height="40" fill="#fbfaf6"/><text x="18" y="675" font-family="Arial,Microsoft YaHei,sans-serif" font-size="12" fill="#676f69">'+note+'</text></svg>';outputs.forEach(out=>fs.writeFileSync(out+'/day-'+(di+1)+'.svg',svg));metadata.push({dayIndex:day.dayIndex,file:'media/routes/day-'+(di+1)+'.svg'});});
const runtime='/* Offline route maps rendered from current itinerary data. */\nwindow.TripRouteMaps={render:function(d,i){var maps='+JSON.stringify(metadata)+';var m=maps.filter(function(m){return m.dayIndex===i});return m.length?m.map(function(m){return \'<img class="trip-route-art" src="\'+m.file+\'" alt="当天真实地图底图、连续路线与地点编号"/>\';}).join(\'\'):""}};\n';
[path.join(output,'trip-route-maps.js')].forEach(p=>fs.writeFileSync(p,runtime));
const sources='# Route map sources\n\nBasemap and place data: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright (ODbL). Offline vector background generated from the current itinerary. Route overlays always follow itinerary array order and are not turn-by-turn navigation.\n';outputs.forEach(out=>fs.writeFileSync(out+'/SOURCES.md',sources));
console.log('Generated '+panels.length+' embedded route map panels for '+days.length+' days.');
