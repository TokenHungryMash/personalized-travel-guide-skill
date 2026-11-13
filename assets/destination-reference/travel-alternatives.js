/* Authored day-specific substitutions. Reading a plan never rewrites the route. */
(()=>{'use strict';
 window.TravelAlternatives={render(d,{P,esc,map}){
  const choices=d.alternatives||[],guard=d.guard?.trim();
  if(!guard&&!choices.length)return '';
  const title=guard&&choices.length?'当天提醒与备选':guard?'当天提醒':'当天备选';
  return `<details class="pocket-reading pocket-weather pocket-alternatives"><summary><span>${title}</span><small>${choices.length?`<span>${choices.length} 个备选</span>`:''}<span class="alternative-toggle" aria-hidden="true"></span></small></summary>${guard?`<section class="pocket-day-guard"><h4>当天提醒</h4><p>${esc(guard)}</p></section>`:''}${choices.length?`<div class="alternative-options">${choices.map((a,i)=>`<details class="alternative-option"><summary><span><small>${esc(a.trigger)}</small><strong>${esc(a.title)}</strong></span><b aria-hidden="true">＋</b></summary><div class="alternative-body"><p>${esc(a.replace)}</p><dl><div><dt>时间</dt><dd>${esc(a.time)}</dd></div><div><dt>走法</dt><dd>${esc(a.traffic)}</dd></div><div><dt>先确认</dt><dd>${esc(a.check)}</dd></div></dl>${a.route.length?`<ul class="alternative-places">${a.route.map(id=>{const p=P[id];return `<li><button data-place="${esc(id)}">${esc(p.name)} <span>详情 ↗</span></button><a href="${esc(map(p))}" target="_blank" rel="noopener" aria-label="导航到${esc(p.name)}">导航 ↗</a></li>`}).join('')}</ul>`:''}</div></details>`).join('')}</div>`:''}</details>`;
 }};
})();
