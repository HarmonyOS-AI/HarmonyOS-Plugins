import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {test} from 'node:test';
const script=path.resolve(import.meta.dirname,'../../../../../plugins/harmonyos-one-multi/skills/hmos-multidevice-h5-layout/scripts/scan-h5-adaptation.mjs');
function scan(files, expectedStatus=0) {
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'h5-scanner-'));
 try {
  for(const [name,text] of Object.entries(files)){const full=path.join(root,name);fs.mkdirSync(path.dirname(full),{recursive:true});fs.writeFileSync(full,text);}
  const result=spawnSync(process.execPath,[script,root],{encoding:'utf8'});
  assert.equal(result.status,expectedStatus,result.stderr);return result.stdout;
 }finally{fs.rmSync(root,{recursive:true,force:true});}
}
test('Web only reports root min-width and exact source location',()=>{
 const output=scan({'web/index.html':'<style>body { min-width:900px }</style>'},1);
 assert.match(output,/H5_ONLY/);assert.match(output,/global-min-width/);assert.match(output,/index\.html:1/);
});
test('ArkTS sources do not receive Web CSS rules',()=>{
 const output=scan({'entry/src/main/ets/pages/Web.ets':"// body { min-width:900px }\nWeb({src:'url'})"});
 assert.match(output,/ARKTS_ONLY/);assert.doesNotMatch(output,/\[high\].*global-min-width/);
});
test('hybrid classification and resize misuse are grounded in actual sources',()=>{
 const output=scan({'web/app.js':"window.addEventListener('resize', refresh());",'entry/src/main/ets/pages/Index.ets':'@Component\nstruct Index {}'},1);
 assert.match(output,/HYBRID/);assert.match(output,/resize-listener-invoked/);
});
test('correct resize listener and responsive root avoid known false positives',()=>{
 const output=scan({'web/app.js':"const root=document.documentElement; function refresh(){root.style.fontSize=root.clientWidth/10+'px';} window.addEventListener('resize', refresh); refresh();",'web/app.css':'body { min-width:0; width:100% }'});
 assert.doesNotMatch(output,/resize-listener-invoked|global-min-width|rem-without-resize-sync/);
});
test('dependency output does not change input classification',()=>{
 const output=scan({'node_modules/lib/index.js':'navigator.userAgent','entry/src/main/ets/X.ets':'@Component struct X {}'});
 assert.match(output,/ARKTS_ONLY/);assert.doesNotMatch(output,/layout-by-ua/);
});
