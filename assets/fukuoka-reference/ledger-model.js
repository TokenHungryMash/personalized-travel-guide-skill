/* JPY integers. Repayments change balances, never travel spending. */
((root)=>{
 function calculate(members,expenses,repayments=[]){
  const balances=Object.fromEntries(members.map(m=>[m,0]));let total=0;
  for(const e of expenses){total+=e.amount;balances[e.payer]+=e.amount;const n=Math.floor(e.amount/e.split.length),r=e.amount%e.split.length;e.split.forEach((m,i)=>balances[m]-=n+(i<r?1:0))}
  for(const r of repayments){balances[r.from]+=r.amount;balances[r.to]-=r.amount}
  const debt=Object.entries(balances).filter(x=>x[1]<0).map(([m,n])=>[m,-n]);
  const credit=Object.entries(balances).filter(x=>x[1]>0).map(x=>[...x]),transfers=[];
  for(let [from,n] of debt)for(const c of credit){const amount=Math.min(n,c[1]);if(amount>0){transfers.push({from,to:c[0],amount});n-=amount;c[1]-=amount}}
  return {total,balances,transfers};
 }
 root.JournalLedger={calculate};
})(typeof window!=='undefined'?window:globalThis);
