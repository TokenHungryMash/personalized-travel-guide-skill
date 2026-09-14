/* Optional existing Playwright runner. Never installs or bypasses host policy. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{pathToFileURL}=require('node:url');
function hashFile(file){return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')}
function reusableCapture(dir,task,row,plan){
 try{return !!row && row.status==='captured' && row.page_sha256===hashFile(path.join(dir,task.page)) && row.day_fingerprint===task.day_fingerprint && row.capture_size===JSON.stringify([plan.width,plan.height,plan.device_scale_factor]) && row.sha256===hashFile(path.join(dir,task.png)) && row.observed_state?.status==='ready' && row.observed_state?.tiles_loaded===true && row.observed_state?.labels===task.stop_numbers.length}catch{return false}
}
async function main(){
 const args=process.argv.slice(2);
 if(!args.length||args.includes('--help')){console.log('node capture_route_maps.cjs <workbench> [--browser <installed browser executable>]\nRequires an already available authorized Playwright/browser. No dependency installation or security workaround.');return;}
 const root=path.resolve(args[0]),dir=path.join(root,'qa','route-capture'),plan=JSON.parse(fs.readFileSync(path.join(dir,'capture-plan.json'),'utf8'));
 let previous=[];try{previous=JSON.parse(fs.readFileSync(path.join(dir,'capture-report.json'),'utf8')).captures||[]}catch{}
 const saved=new Map(previous.map(row=>[row.png,row]));
 if(plan.tasks.length && plan.tasks.every(task=>reusableCapture(dir,task,saved.get(task.png),plan))){console.log('All '+plan.tasks.length+' captures unchanged; reusing exact bytes and existing review states.');return;}
 let chromium;
 const driverArg=args.indexOf('--driver');
 if(driverArg>=0){
  if(!args[driverArg+1])throw Error('--driver requires an installed playwright or playwright-core module path');
  ({chromium}=require(path.resolve(args[driverArg+1])));
 }else{
  try{({chromium}=require('playwright'))}catch(e){
   try{({chromium}=require('playwright-core'))}catch(e){throw Error('Playwright unavailable. Provide --driver for an authorized isolated installation, or use the host-authorized browser. Do not loop through installation attempts.')}
  }
 }
 const browserArg=args.indexOf('--browser'),browser=await chromium.launch({headless:true,...(browserArg>=0?{executablePath:args[browserArg+1]}:{})});
 const report={captures:previous.filter(row=>plan.tasks.some(task=>task.png===row.png)),status:'in_progress'};let failures=0;
 try{
  const context=await browser.newContext({viewport:{width:plan.width,height:plan.height},deviceScaleFactor:plan.device_scale_factor});
  for(const task of plan.tasks){
   if(reusableCapture(dir,task,saved.get(task.png),plan)){console.log(task.png+': cached');continue;}
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   page.on('requestfailed',r=>errors.push(r.url()+': '+r.failure()?.errorText));
   const row={png:task.png,page:task.page,status:'failed',visual_reviewed:false};
   try{
    await page.goto(pathToFileURL(path.join(dir,task.page)).href,{waitUntil:'load',timeout:45000});
    await page.waitForFunction(()=>window.CAPTURE_STATE&&window.CAPTURE_STATE.status!=='loading',{},{timeout:50000});
    const state=await page.evaluate(()=>window.CAPTURE_STATE);if(state.status!=='ready')throw Error(JSON.stringify(state));
    const target=path.join(dir,task.png);await page.locator('#sheet').screenshot({path:target,timeout:10000});
    row.status='captured';row.sha256=hashFile(target);row.observed_state=state;
    row.page_sha256=hashFile(path.join(dir,task.page));row.day_fingerprint=task.day_fingerprint;row.capture_size=JSON.stringify([plan.width,plan.height,plan.device_scale_factor]);
   }catch(e){row.error=e.message;failures++;}
   row.diagnostics=errors;report.captures=report.captures.filter(old=>old.png!==row.png);report.captures.push(row);fs.writeFileSync(path.join(dir,'capture-report.json'),JSON.stringify(report,null,2));await page.close();
   console.log(task.png+': '+row.status);
   if(failures>=2){console.log('Two failed capture views; stop and inspect diagnostics. No automatic browser/URL bypass.');break;}
  }
 }finally{await browser.close();}
 report.status=failures?'failed':'captured_pending_visual_review';fs.writeFileSync(path.join(dir,'capture-report.json'),JSON.stringify(report,null,2));
 if(failures)process.exitCode=2;
}
if(require.main===module)main().catch(e=>{console.error(e.message);process.exitCode=2});
module.exports={reusableCapture};
