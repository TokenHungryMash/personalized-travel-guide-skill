/* All arithmetic is performed in currency minor units. Legacy records use the edition currency. */
((root)=>{
 const digits=c=>['JPY','KRW','IDR','VND'].includes(c)?0:2;
 function calculate(members,expenses,repayments=[],precision=0){
  const factor=10**precision,unit=n=>Math.round(n*factor),b=Object.fromEntries(members.map(m=>[m,0]));let total=0;
  for(const e of expenses){const amount=unit(e.amount);if(!Number.isSafeInteger(amount)||amount<=0||!members.includes(e.payer)||!e.split?.length||e.split.some(m=>!members.includes(m)))throw Error('Invalid ledger record');total+=amount;b[e.payer]+=amount;const share=Math.floor(amount/e.split.length),remainder=amount%e.split.length;e.split.forEach((m,i)=>b[m]-=share+(i<remainder?1:0))}
  for(const r of repayments){if(!members.includes(r.from)||!members.includes(r.to)||r.from===r.to)throw Error('Invalid repayment');b[r.from]+=unit(r.amount);b[r.to]-=unit(r.amount)}
  const debt=Object.entries(b).filter(x=>x[1]<0).map(([m,n])=>[m,-n]),credit=Object.entries(b).filter(x=>x[1]>0).map(x=>[...x]),transfers=[];
  for(let [from,n] of debt)for(const c of credit){const amount=Math.min(n,c[1]);if(amount>0){transfers.push({from,to:c[0],amount:amount/factor});n-=amount;c[1]-=amount}}
  return {total:total/factor,balances:Object.fromEntries(Object.entries(b).map(([m,n])=>[m,n/factor])),transfers};
 }
 function byCurrency(members,expenses,repayments=[],base='JPY'){
  const currencies=[...new Set([...expenses,...repayments].map(e=>e.currency||base))];
  return Object.fromEntries(currencies.map(c=>[c,calculate(members,expenses.filter(e=>(e.currency||base)===c),repayments.filter(e=>(e.currency||base)===c),digits(c))]));
 }
 root.JournalLedger={calculate,byCurrency,digits};
})(typeof window!=='undefined'?window:globalThis);
