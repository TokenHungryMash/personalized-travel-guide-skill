/* Published itinerary only. Legacy custom routes and times are not applied. */
(function(root){
function minutes(s){if(!/^\d{2}:\d{2}$/.test(s||''))return null;const [h,m]=s.split(':').map(Number);return h<24&&m<60?h*60+m:null}
function clock(n){return (n>=1440?'次日 ':'')+String(Math.floor(n/60)%24).padStart(2,'0')+':'+String(n%60).padStart(2,'0')}
function plan(day){
 const ids=day.stops.map(s=>s[1]),preset=day.schedules.standard;
 let cursor=minutes(day.start)??540;
 return ids.map((id,i)=>{const authored=preset[id],duration=authored.duration;
  const transfer=i?day.transfers[ids[i-1]+'>'+id]:null;
  const start=Math.max(minutes(authored.time)??cursor,cursor+(transfer?.minutes||0));
  cursor=start+duration;
  return {id,start,end:cursor,time:clock(start),endTime:clock(cursor),duration,transfer,label:'建议时段',guard:authored.guard||'给下一站留出交通时间。'};
 });
}
root.TravelSchedule={plan,minutes,clock};
})(typeof window!=='undefined'?window:globalThis);
