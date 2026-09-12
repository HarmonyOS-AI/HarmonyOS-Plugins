import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {isolatedEnvironment,startServer,executeSession} from './opencode.mjs';
import {installFixture} from './fixtures.mjs';
import {snapshot,changes,writeJson,digest} from './artifacts.mjs';

export const repo=path.resolve(import.meta.dirname,'../../../..');
export const behaviorRoot=import.meta.dirname;
export async function verifyFrozen(){
 const frozen=JSON.parse(await fs.readFile(path.join(behaviorRoot,'frozen.json'),'utf8'));
 for(const [file,hash] of Object.entries(frozen.files))if(digest(await fs.readFile(path.join(behaviorRoot,file)))!==hash)throw new Error(`Frozen evaluation input changed: ${file}`);
 return frozen;
}
export async function runCase(test,side,repetition,outputRoot,sourceRoot,model){
 const destination=path.join(outputRoot,`${side}-${test.id}-${repetition}.json`);
 const sourceSha256=digest(JSON.stringify(await snapshot(sourceRoot)));
 try{const cached=JSON.parse(await fs.readFile(destination,'utf8'));if(cached.sourceSha256!==sourceSha256||cached.model!==model)throw new Error('Source/config changed; use a new evaluation output directory');return cached;}catch(error){if(error.code!=='ENOENT')throw error;}
 const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'one-multi-agent-'));
 const workspace=path.join(temporary,'project'),plugin=path.join(temporary,'plugin');
 await fs.mkdir(workspace,{recursive:true});
 await fs.cp(sourceRoot,plugin,{recursive:true});
 await fs.symlink(path.join(repo,'node_modules'),path.join(plugin,'node_modules'),'dir');
 await installFixture(workspace,test.fixture,plugin);
 const before=await snapshot(workspace);
 const fixtureSha256=digest(JSON.stringify(Object.fromEntries(Object.entries(before).filter(([file])=>!/^\.onemulti\/(scripts|references|assets)\//.test(file)&&file!=='.onemulti/SKILL.md'))));
 let server,result;
 const rubric=JSON.parse(await fs.readFile(path.join(behaviorRoot,'rubric.json'),'utf8'));
 const progressFile=path.join(outputRoot,`progress-${side}-${test.id}-${repetition}.json`);
 const onProgress=progress=>writeJson(progressFile,{caseId:test.id,side,repetition,...progress});
 try{
   server=await startServer(await isolatedEnvironment(temporary,workspace,plugin,model));
   result=await executeSession(server,{prompt:test.prompt,model,timeoutSeconds:rubric.limits.sessionTimeoutSeconds,boundary:test.requireQuestion,maxQuestions:rubric.limits.maxQuestions,fixedAnswers:rubric.fixedAnswers,onProgress});
 }catch(error){result={status:'environment_error',error:error.message,messages:[],questions:[]};}
 finally{await server?.close();}
 const after=await snapshot(workspace);
 const pluginChanged=digest(JSON.stringify(await snapshot(plugin)))!==sourceSha256;
 const record={caseId:test.id,domain:test.domain,split:test.split,side,repetition,model,sourceSha256,fixtureSha256,fixtureType:'synthetic-no-sdk-or-device',pluginChanged,...result,before,after,changedFiles:changes(before,after)};
 await writeJson(destination,record);await fs.rm(progressFile,{force:true});await fs.rm(temporary,{recursive:true,force:true});
 console.log(`${side} ${test.id} #${repetition}: ${record.status} (${Math.round((record.elapsedMs??0)/1000)}s)`);
 return record;
}
export async function prepareSources(outputRoot,baseline){
 await fs.mkdir(outputRoot,{recursive:true});
 const baselineRoot=path.join(outputRoot,'baseline-source');
 try{await fs.access(path.join(baselineRoot,'plugin.config.json'));}catch{
   const extracted=await fs.mkdtemp(path.join(os.tmpdir(),'one-multi-baseline-'));
   const archive=execFileSync('git',['archive',baseline,'plugins/harmonyos-one-multi'],{cwd:repo,maxBuffer:8*1024*1024});
   execFileSync('tar',['-x','-C',extracted],{input:archive});
   await fs.cp(path.join(extracted,'plugins/harmonyos-one-multi'),baselineRoot,{recursive:true});
   await fs.rm(extracted,{recursive:true,force:true});
 }
 return baselineRoot;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 const frozen=await verifyFrozen(),cases=JSON.parse(await fs.readFile(path.join(behaviorRoot,'cases.json'),'utf8'));
 const outputRoot=path.resolve(process.argv[2]??path.join(repo,'.eval-runs/one-multi/p1'));
 const test=cases.find(c=>c.id===(process.argv[3]??'workflow-analysis'));if(!test)throw new Error('Unknown case');
 const side=process.argv[4]??'baseline',base=await prepareSources(outputRoot,frozen.baseline);
 const result=await runCase(test,side,0,outputRoot,side==='baseline'?base:path.join(repo,'plugins/harmonyos-one-multi'),'bailian-blue/qwen3.8-max');
 if(result.status!=='completed')process.exitCode=1;
}
