const assert=require('node:assert/strict'),calculate=require('./settlement.js');
const members=['a','b','c'].map(id=>({id,name:id}));
const expense=(payer,amount,participants,currency='CNY',kind='expense')=>({payer,amount,participants,currency,kind});
let s=calculate([expense('a',100,['a','b']),expense('b',40,['a','b'])],members).CNY;
assert.deepEqual(s.balances,{a:3000,b:-3000,c:0});assert.deepEqual(s.transfers,[{from:'b',to:'a',amount:30}]);
s=calculate([expense('a',100,['a','b']),expense('b',40,['a','b']),expense('b',30,['a'],'CNY','settlement')],members).CNY;
assert.equal(s.total,14000);assert.equal(s.transfers.length,0);
s=calculate([expense('a',100,['a','b','c'])],members).CNY;assert.deepEqual(s.balances,{a:6666,b:-3333,c:-3333});
assert.equal(Object.values(s.balances).reduce((a,b)=>a+b,0),0);
s=calculate([expense('b',10,['b']),expense('a',99,['b'],'IDR')],members);assert.equal(s.CNY.transfers.length,0);assert.equal(s.IDR.transfers[0].amount,99);
// Property checks: every generated transfer reduces balances exactly to zero.
for(let n=1;n<=150;n++){const rows=Array.from({length:n%17+1},(_,i)=>expense(members[(i+n)%3].id,(n*17+i*13)/100,members.slice(0,i%3+1).map(m=>m.id)));const r=calculate(rows,members).CNY;const balance={...r.balances};for(const t of r.transfers){balance[t.from]+=Math.round(t.amount*100);balance[t.to]-=Math.round(t.amount*100);}assert.ok(Object.values(balance).every(v=>v===0));}
console.log('PASS: 2/3-person netting, rounding, self-only expenses, currencies, repayment and 150 balance checks');
