// Synthetic cache fixtures only; these bytes are not real maps or QA evidence.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {reusableCapture}=require('./capture_route_maps.cjs');
test('capture resume binds page, route, image, size and readiness without inventing review',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'capture-resume-'));
 try{
  fs.writeFileSync(path.join(dir,'a.html'),'synthetic page');fs.writeFileSync(path.join(dir,'a.png'),'synthetic pixels');
  const hash=n=>crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,n))).digest('hex');
  const task={page:'a.html',png:'a.png',day_fingerprint:'route-a',stop_numbers:[1,2]},plan={width:1400,height:1100,device_scale_factor:1};
  const row={status:'captured',page_sha256:hash('a.html'),sha256:hash('a.png'),day_fingerprint:'route-a',capture_size:'[1400,1100,1]',observed_state:{status:'ready',tiles_loaded:true,labels:2},visual_reviewed:false};
  assert.equal(reusableCapture(dir,task,row,plan),true);assert.equal(row.visual_reviewed,false);
  // A cached CLI run must work even with an unavailable driver: no browser starts.
  const root=path.join(dir,'build'),captureDir=path.join(root,'qa','route-capture');fs.mkdirSync(captureDir,{recursive:true});
  for(const name of ['a.html','a.png'])fs.copyFileSync(path.join(dir,name),path.join(captureDir,name));
  fs.writeFileSync(path.join(captureDir,'capture-plan.json'),JSON.stringify({...plan,tasks:[task]}));
  fs.writeFileSync(path.join(captureDir,'capture-report.json'),JSON.stringify({captures:[{...row,png:'a.png',page:'a.html'}]}));
  const child=require('node:child_process').spawnSync(process.execPath,[path.join(__dirname,'capture_route_maps.cjs'),root,'--driver',path.join(dir,'nonexistent-driver')],{encoding:'utf8'});
  assert.equal(child.status,0,child.stderr);assert.match(child.stdout,/captures unchanged/);
  assert.equal(reusableCapture(dir,{...task,day_fingerprint:'route-b'},row,plan),false);
  assert.equal(reusableCapture(dir,task,row,{...plan,width:1600}),false);
  assert.equal(reusableCapture(dir,task,{...row,observed_state:{status:'loading'}},plan),false);
  fs.writeFileSync(path.join(dir,'a.png'),'changed');assert.equal(reusableCapture(dir,task,row,plan),false);
  row.sha256=hash('a.png');fs.writeFileSync(path.join(dir,'a.html'),'changed labels');assert.equal(reusableCapture(dir,task,row,plan),false);
 }finally{fs.rmSync(dir,{recursive:true,force:true})}
});
