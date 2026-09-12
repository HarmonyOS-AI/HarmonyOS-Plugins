import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
test('route registration, route table references and ledger contracts',()=>{
 const result=spawnSync('python3',[new URL('./p1-regression.py',import.meta.url).pathname],{encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
 assert.equal(result.status,0,result.stdout+result.stderr);
});

import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {installFixture,pagePath} from '../behavior/fixtures.mjs';
const plugin=path.resolve(import.meta.dirname,'../../../../plugins/harmonyos-one-multi');
const run=(file,args,options={})=>spawnSync('python3',[file,...args],{encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1',...(options.env||{})},...(options.input!==undefined?{input:options.input}:{})});

async function driveToVerification(root){
 const om=path.join(root,'.onemulti'),ledgerFile=path.join(om,'decisions.json');
 const ledger=JSON.parse(await fs.readFile(ledgerFile));
 const batch=ledger.batches[0],issue=ledger.issues[0];
 batch.status='executing';batch.specConfirmed=true;ledger.task.status='executing';
 issue.changeStatus='modified';issue.changedFiles=[pagePath('B01')];issue.changeSummary='Use available parent width';
 await fs.writeFile(ledgerFile,JSON.stringify(ledger));
 return {om,ledgerFile};
}

test('basic-only completion records honest missing-device results and a validated report',async()=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'basic-completion-'));
 try{
  await installFixture(root,'workflow',plugin);
  const {om,ledgerFile}=await driveToVerification(root);
  const preflight=path.join(om,'scripts/verification/preflight.py');
  const foundation=path.join(om,'scripts/verification/run-foundation.py');
  const ledgerCli=path.join(om,'scripts/task-ledger.py');
  assert.equal(run(preflight,['begin',root]).status,0);
  const probe=JSON.parse(run(preflight,['record-multimodal',root,'--available','--description','synthetic probe']).stdout);
  assert.equal(probe.next,'ask-test-scope');
  const scope=JSON.parse(run(preflight,['record-test-scope',root,'--choice','basic_only']).stdout);
  assert.equal(scope.next,'record-static-only-results');
  const page=path.join(root,pagePath('B01'));
  await fs.writeFile(page,(await fs.readFile(page,'utf8')).replace('.width(360)',".width('100%')"));
  const bin=path.join(root,'bin');await fs.mkdir(bin);
  await fs.writeFile(path.join(bin,'devecocli'),'#!/bin/sh\necho "Synthetic test: no actual compilation"\nexit 0\n',{mode:0o755});
  const foundationResult=run(foundation,[root],{env:{PATH:`${bin}:${process.env.PATH}`}});
  assert.equal(foundationResult.status,0,foundationResult.stdout+foundationResult.stderr);
  assert.equal(JSON.parse(foundationResult.stdout).ok,true);
  for(const form of ['phone','tablet']){
   const input=JSON.stringify({form,checkId:'row-width',status:'not_verified',reason:'device_unavailable'});
   const recorded=run(ledgerCli,['put-verification',ledgerFile,'B01-UI-001','--input','-'],{input});
   assert.equal(recorded.status,0,recorded.stdout+recorded.stderr);
  }
  assert.equal(run(path.join(om,'scripts/render-report.py'),[om,'--batch-id','B01']).status,0);
  assert.ok((await fs.readFile(path.join(om,'adaptation-report-B01.html'),'utf8')).includes('未验证'));
  const done=run(ledgerCli,['transition-batch',ledgerFile,'B01','--input','-'],{input:JSON.stringify({batch:{status:'completed'}})});
  assert.equal(done.status,0,done.stdout+done.stderr);
  const after=JSON.parse(await fs.readFile(ledgerFile));
  assert.equal(after.batches[0].status,'completed');
  assert.equal(after.issues[0].verificationResults.length,2);
  assert.ok(after.issues[0].verificationResults.every(r=>r.status==='not_verified'));
  assert.equal(after.issues[1].changeStatus,'pending');
  assert.equal(after.task.status,'executing');
 }finally{await fs.rm(root,{recursive:true,force:true});}
});

test('preflight refuses to continue after the frozen verificationPlan changes',async()=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'frozen-plan-'));
 try{
  await installFixture(root,'workflow',plugin);
  const {om}=await driveToVerification(root);
  const preflight=path.join(om,'scripts/verification/preflight.py');
  assert.equal(run(preflight,['begin',root]).status,0);
  const ledgerFile=path.join(om,'decisions.json');
  const changed=JSON.parse(await fs.readFile(ledgerFile));
  changed.issues[0].verificationPlan[0].check='Changed scope without confirmation';
  await fs.writeFile(ledgerFile,JSON.stringify(changed));
  const denied=run(preflight,['record-multimodal',root,'--available','--description','synthetic probe']);
  assert.notEqual(denied.status,0,'frozen verificationPlan must stop verification');
  assert.ok(denied.stderr.includes('冻结'));
 }finally{await fs.rm(root,{recursive:true,force:true});}
});
