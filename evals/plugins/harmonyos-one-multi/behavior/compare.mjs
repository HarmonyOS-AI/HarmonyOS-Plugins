import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {execFileSync,spawnSync} from 'node:child_process';
import {repo,behaviorRoot,verifyFrozen,prepareSources,runCase} from './run-case.mjs';
import {snapshot,digest,writeJson} from './artifacts.mjs';
import {resourceLinks} from '../lib/resource-links.mjs';
import {judgePair} from './judge.mjs';
import {summarize,writeReport} from './report.mjs';

function option(name,fallback){const index=process.argv.indexOf(name);return index<0?fallback:process.argv[index+1];}
const output=path.resolve(option('--output',path.join(repo,'.eval-runs/one-multi/p1-final')));
const split=option('--split','all');if(!['all','development'].includes(split))throw new Error('--split must be all or development');
const frozen=await verifyFrozen(),rubric=JSON.parse(await fs.readFile(path.join(behaviorRoot,'rubric.json')));
const selectedCase=option('--case',null);
const allCases=JSON.parse(await fs.readFile(path.join(behaviorRoot,'cases.json'))),cases=allCases.filter(c=>(split==='all'||c.split===split)&&(!selectedCase||c.id===selectedCase));
if(!cases.length)throw new Error('No matching cases');
const version=execFileSync('opencode',['--version'],{encoding:'utf8'}).trim();if(version!==rubric.opencodeVersion)throw new Error(`OpenCode version ${version} does not match frozen ${rubric.opencodeVersion}`);
const baseline=await prepareSources(output,frozen.baseline),candidate=path.join(output,'candidate-source');
const workingSource=path.join(repo,'plugins/harmonyos-one-multi');
const candidateSha=digest(JSON.stringify(await snapshot(workingSource)));
try{await fs.access(candidate);}catch{await fs.cp(workingSource,candidate,{recursive:true,filter:source=>!source.includes('__pycache__')&&!source.endsWith('.pyc')});}
if(digest(JSON.stringify(await snapshot(candidate)))!==candidateSha)throw new Error('Candidate changed since this comparison began. Retain this run and choose a new output directory.');
const evaluatorSha256=digest(JSON.stringify(await snapshot(behaviorRoot))+(await fs.readFile(path.join(behaviorRoot,'../lib/resource-links.mjs')))+(await fs.readFile(path.join(behaviorRoot,'../tests/p1-regression.py'))));
const providerConfig=JSON.parse(await fs.readFile(path.join(os.homedir(),'.config/opencode/opencode.json'))).provider[rubric.model.split('/')[0]];
const providerConfigurationSha256=digest(JSON.stringify(providerConfig));
const configuration={evaluatorSha256,providerConfigurationSha256,baselineSourceSha256:digest(JSON.stringify(await snapshot(baseline))),baseline:frozen.baseline,candidateSourceSha256:candidateSha,candidateGitHead:execFileSync('git',['rev-parse','HEAD'],{cwd:repo,encoding:'utf8'}).trim(),model:rubric.model,opencodeVersion:version,nodeVersion:process.version,dependencyLockSha256:digest(await fs.readFile(path.join(repo,'package-lock.json'))),protocol:frozen,permissions:'allow project tools and the specific external plugin runtime directory; deny other external directories, task delegation and web; synthetic build/device commands',limits:rubric.limits,startedAt:new Date().toISOString()};
try{const saved=JSON.parse(await fs.readFile(path.join(output,'configuration.json')));
 for(const key of ['evaluatorSha256','providerConfigurationSha256','dependencyLockSha256','model','nodeVersion','opencodeVersion'])if(saved[key]!==configuration[key])throw new Error(`Comparison configuration changed (${key}); use a new output directory`);
 Object.assign(configuration,saved);}catch(error){if(error.code!=='ENOENT')throw error;}
await writeJson(path.join(output,'configuration.json'),configuration);
await fs.mkdir(path.join(output,'protocol'),{recursive:true});for(const file of ['cases.json','rubric.json','fixtures.mjs','frozen.json'])await fs.copyFile(path.join(behaviorRoot,file),path.join(output,'protocol',file));
const deterministic={};
for(const [side,source] of Object.entries({baseline,candidate})){
 const result=spawnSync('python3',[path.join(behaviorRoot,'../tests/p1-regression.py')],{cwd:repo,encoding:'utf8',env:{...process.env,PLUGIN_ROOT:source,PYTHONDONTWRITEBYTECODE:'1'}});
 deterministic[side]={exitCode:result.status,stdout:result.stdout,stderr:result.stderr,brokenLinks:resourceLinks(source)};
}
await writeJson(path.join(output,'deterministic.json'),deterministic);
if(deterministic.candidate.exitCode!==0||deterministic.candidate.brokenLinks.length)throw new Error('Candidate deterministic checks failed; see deterministic.json');
const jobs=[];
for(let repetition=0;repetition<rubric.repeats;repetition++)for(const test of cases)jobs.push({test,repetition});
let next=0;const records=[],judges=[];
// Two actor calls per pair overlap. Pairs alternate ordering, and judge calls are serial.
for(const job of jobs){
 try{await fs.access(path.join(output,"STOP_AFTER_PAIR"));console.log("Stopped after completed pair; raw evidence retained.");break;}catch(error){if(error.code!=="ENOENT")throw error;}
 const order=(next++%2)?['candidate','baseline']:['baseline','candidate'];
 const pair=await Promise.all(order.map(side=>runCase(job.test,side,job.repetition,output,side==='baseline'?baseline:candidate,rubric.model)));
 records.push(...pair);
 const bySide=Object.fromEntries(pair.map(r=>[r.side,r]));
 if(bySide.baseline.fixtureSha256!==bySide.candidate.fixtureSha256)throw new Error('Input fixture differs between versions; raw runs retained, comparison halted');
 judges.push(await judgePair(job.test,bySide.baseline,bySide.candidate,output,rubric));
 await writeReport(output,summarize(cases,records,judges,rubric),configuration,deterministic);
}
const summary=await writeReport(output,summarize(cases,records,judges,rubric),configuration,deterministic);
console.log(JSON.stringify({report:path.join(output,'comparison.html'),qualityImproved:summary.qualityImproved,gates:summary.gates,metrics:summary.metrics},null,2));
if(split==='all'&&!summary.qualityImproved)process.exitCode=1;
