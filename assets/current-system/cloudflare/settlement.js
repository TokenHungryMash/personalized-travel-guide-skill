/* Integer minor units: equal splits keep every cent; currencies never mix. */
(function(root){
function calculate(records,members){
 const currencies={};
 for(const r of records){
  const cents=Math.round(r.amount*100),ids=[...r.participants].sort();
  const c=currencies[r.currency]||(currencies[r.currency]={total:0,balances:Object.fromEntries(members.map(m=>[m.id,0])),transfers:[]});
  if(!ids.length||!members.some(m=>m.id===r.payer)){if(r.kind!=='settlement')c.total+=cents;c.unresolved=(c.unresolved||0)+1;continue;}
  c.balances[r.payer]=(c.balances[r.payer]||0)+cents;
  if(r.kind!=='settlement')c.total+=cents;
  const base=Math.floor(cents/ids.length),remainder=cents%ids.length;
  ids.forEach((id,i)=>c.balances[id]=(c.balances[id]||0)-base-(i<remainder?1:0));
 }
 for(const c of Object.values(currencies)){
  const debtors=Object.entries(c.balances).filter(([,v])=>v<0).map(([id,v])=>({id,n:-v})).sort((a,b)=>b.n-a.n||a.id.localeCompare(b.id));
  const creditors=Object.entries(c.balances).filter(([,v])=>v>0).map(([id,v])=>({id,n:v})).sort((a,b)=>b.n-a.n||a.id.localeCompare(b.id));
  let i=0,j=0;
  while(i<debtors.length&&j<creditors.length){const a=debtors[i],b=creditors[j],amount=Math.min(a.n,b.n);c.transfers.push({from:a.id,to:b.id,amount:amount/100});a.n-=amount;b.n-=amount;if(!a.n)i++;if(!b.n)j++;}
 }
 return currencies;
}
if(typeof module!=='undefined')module.exports=calculate;else root.calculateTravelSettlement=calculate;
})(globalThis);
