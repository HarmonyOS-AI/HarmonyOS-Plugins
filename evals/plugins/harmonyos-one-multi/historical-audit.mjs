import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const root=path.resolve(import.meta.dirname,'../../..');
const baseline='c7213b1b43d1d060f5e428d7278f1ba3db38ee3e';
const inventory=JSON.parse(fs.readFileSync(new URL('./migration-inventory.json',import.meta.url)));
assert.equal(inventory.files.length,230);
for(const file of inventory.files){
  const historical=execFileSync('git',['show',`${baseline}:${file.destination}`],{cwd:root,maxBuffer:8*1024*1024});
  assert.equal(createHash('sha256').update(historical).digest('hex'),file.sourceSha256,file.destination);
}
console.log(JSON.stringify({audit:'historical-migration',baseline,files:inventory.files.length,passed:true}));
