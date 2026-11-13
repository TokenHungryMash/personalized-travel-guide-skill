// Run against any current destination workbench. No third-party test dependencies.
const assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(process.argv[2]||path.join(__dirname,'../assets/destination-reference'));require(path.join(root,'ledger-model.js'));const L=globalThis.JournalLedger;
const members=['甲','乙','丙'];
const e={amount:100,payer:'甲',split:members};let v=L.calculate(members,[e]);assert.equal(v.total,100);assert.deepEqual(v.balances,{甲:66,乙:-33,丙:-33});assert.equal(Object.values(v.balances).reduce((a,b)=>a+b,0),0);
v=L.calculate(members,[e],[{from:'乙',to:'甲',amount:33}]);assert.equal(v.total,100);assert.equal(v.balances.乙,0);assert.deepEqual(v.transfers,[{from:'丙',to:'甲',amount:33}]);
const g=L.byCurrency(members,[e,{...e,amount:.01,currency:'CNY'}],[],'JPY');assert.equal(g.JPY.total,100);assert.equal(g.CNY.total,.01);assert.deepEqual(g.CNY.balances,{甲:0,乙:0,丙:0});
v=L.calculate(['甲','乙'],[{amount:10.01,payer:'甲',split:['甲','乙']}],[],2);assert.deepEqual(v.balances,{甲:5,乙:-5});
v=L.calculate([...members,'丁'],[e]);assert.equal(v.balances.丁,0);assert.equal(v.total,100);
console.log('PASS ledger: exact remainder, balance conservation, repayments, separate currencies, fractional amount, legacy currency and new member isolation.');

// Optional real-browser persistence regression. Existing model checks remain dependency-free.
// Usage: node check_ledger.cjs WORKBENCH --browser [--html index.html]
async function checkPersistenceFailure(){
 const fs=require('node:fs'),{pathToFileURL}=require('node:url');
 const {chromium,executablePath}=require('./browser_runtime.cjs').browserRuntime(root);
 const edition=JSON.parse(fs.readFileSync(path.join(root,'edition.json'),'utf8'));
 const manifestPath=path.join(root,'build-manifest.json');
 const manifest=fs.existsSync(manifestPath)?JSON.parse(fs.readFileSync(manifestPath,'utf8')):{};
 const htmlIndex=process.argv.indexOf('--html');
 if(htmlIndex>=0&&!process.argv[htmlIndex+1])throw Error('--html requires a filename');
 const filename=htmlIndex>=0?process.argv[htmlIndex+1]:(manifest.artifact||'index.html');
 const target=path.resolve(root,filename),isFinal=!!manifest.artifact&&target===path.resolve(root,manifest.artifact);
 const sha256=require('node:crypto').createHash('sha256').update(fs.readFileSync(target)).digest('hex');
 if(isFinal)assert.equal(sha256,manifest.sha256,'final artifact does not match build-manifest.json');
 const key='travel-magazine-v4-'+edition.slug,browser=await chromium.launch({executablePath});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce',acceptDownloads:true});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const persisted=()=>page.evaluate(k=>JSON.parse(localStorage.getItem(k)),key);
  const openLedger=async()=>{await page.locator('#pocket-open').click();await page.locator('#pocket-dialog [data-tool=ledger]').click()};
  const saveExpense=async(title,amount)=>{await page.locator('#expense-form [name=title]').fill(title);await page.locator('#expense-form [name=amount]').fill(String(amount));await page.locator('#expense-form [type=submit]').click()};
  await page.goto(pathToFileURL(target).href);await openLedger();
  await saveExpense('QA saved expense',100);
  assert.match(await page.locator('#expense-message').textContent(),/^已保存/);
  await page.locator('.ledger-member-fold').evaluate(e=>e.open=true);
  await page.locator('#member-form [name=member]').fill('QA同行');await page.locator('#member-form [type=submit]').click();
  const before=await persisted();assert.equal(before.expenses.length,1);assert.equal(before.members.length,2);
  // Throw from the actual storage API after a known-good record has been saved.
  await page.evaluate(k=>{window.__qaLedgerSetItem=Storage.prototype.setItem;Storage.prototype.setItem=function(name,value){if(name===k)throw new DOMException('QA storage quota exceeded','QuotaExceededError');return window.__qaLedgerSetItem.call(this,name,value)}},key);
  await saveExpense('QA unsaved expense',200);
  assert.match(await page.locator('#expense-message').textContent(),/已记在本页，但未保存到本机/);
  assert.equal(await page.locator('#expense-list .expense-row').count(),2);
  assert.deepEqual(await persisted(),before,'failed save must leave the persisted original unchanged');
  await page.locator('#expense-list .expense-row').filter({hasText:'QA saved expense'}).locator('[data-edit-expense]').click();
  await page.locator('#expense-form [name=amount]').fill('125');await page.locator('#expense-form [type=submit]').click();
  assert.match(await page.locator('#expense-message').textContent(),/未保存到本机/);
  await page.locator('#ledger-repayment-form [name=from]').selectOption(before.members[1]);
  await page.locator('#ledger-repayment-form [name=to]').selectOption(before.members[0]);
  await page.locator('#ledger-repayment-form [name=amount]').fill('10');
  await page.locator('#ledger-repayment-form button').click();
  assert.match(await page.locator('#ledger-repayment-status').textContent(),/还款已记在本页，但未保存到本机/);
  assert.equal(await page.locator('[data-ledger-delete-repay]').count(),1);
  assert.deepEqual(await persisted(),before,'failed edit and repayment must not overwrite saved data');
  // Export must still rescue the in-memory records while localStorage is unavailable.
  await page.locator('#ledger-dialog [data-close]').click();
  const pending=page.waitForEvent('download');await page.locator('#export-data').click();
  const download=await pending,payload=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
  assert.equal(payload.state.expenses.length,2);assert.equal(payload.state.repayments.length,1);
  assert.equal(payload.state.expenses.find(e=>e.title==='QA saved expense').amount,125);
  assert.equal(payload.state.expenses.find(e=>e.title==='QA unsaved expense').amount,200);
  assert.equal(payload.state.repayments[0].amount,10);
  assert.deepEqual(await persisted(),before);
  // Recovery saves the retained in-memory state, then survives a fresh page load.
  await page.evaluate(()=>{Storage.prototype.setItem=window.__qaLedgerSetItem;delete window.__qaLedgerSetItem});
  await openLedger();await saveExpense('QA recovered expense',5);
  assert.match(await page.locator('#expense-message').textContent(),/^已保存/);
  assert.equal((await persisted()).expenses.length,3);assert.equal((await persisted()).repayments.length,1);
  await page.reload();await openLedger();assert.equal(await page.locator('#expense-list .expense-row').count(),3);
  assert.equal(await page.locator('[data-ledger-delete-repay]').count(),1);assert.deepEqual(errors,[]);
  const output=path.join(root,'qa-ledger');fs.mkdirSync(output,{recursive:true});
  fs.writeFileSync(path.join(output,'persistence-report.json'),JSON.stringify({result:'pass',mode:isFinal?'final-artifact':'source-preview',html:filename,sha256,buildId:isFinal?manifest.buildId:null,checks:['successful save','failed new expense retained in memory','failed edit retained in memory','failed repayment visible in dialog','persisted originals untouched','backup rescues unsaved records','storage recovery and reload'],errors},null,2));
  await context.close();console.log('PASS browser ledger persistence failure: truthful status, retained records, backup rescue and recovery.');
 }finally{await browser.close()}
}
if(process.argv.includes('--browser'))checkPersistenceFailure().catch(error=>{console.error(error);process.exitCode=1});
