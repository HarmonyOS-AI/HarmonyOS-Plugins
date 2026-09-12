import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {gradeToolSource} from './grade-tool.mjs';

export async function isolatedEnvironment(root, workspace, plugin, model, options={}) {
  const configHome=path.join(root,'config'), dataHome=path.join(root,'data');
  await fs.mkdir(path.join(configHome,'opencode'),{recursive:true});
  await fs.mkdir(path.join(dataHome,'opencode'),{recursive:true});
  const original=JSON.parse(await fs.readFile(path.join(os.homedir(),'.config/opencode/opencode.json'),'utf8'));
  const provider=model.split('/')[0];
  if(!original.provider?.[provider])throw new Error(`Provider ${provider} is not configured`);
  const bin=path.join(root,'bin');
  const isolationPlugin=path.join(root,'isolation.mjs');
  const shellQuote=value=>"'"+value.replaceAll("'", "'\"'\"'")+"'";
  const pathPrefix=`export PATH=${shellQuote(`${bin}:${process.env.PATH}`)}\n`;
  await fs.writeFile(isolationPlugin,`export default async () => ({'tool.execute.before': async (input, output) => { if(input.tool === 'bash') output.args.command = ${JSON.stringify(pathPrefix)} + output.args.command; }});`);
  const gradePlugin=path.join(root,'grade-tool.mjs');
  if(options.judge)await fs.writeFile(gradePlugin,gradeToolSource(options.criteriaCount,import.meta.resolve('@opencode-ai/plugin')));
  const realPlugin=plugin?await fs.realpath(plugin):null;
  const externalAccess=plugin?{'*':'deny',[plugin]:'allow',[`${plugin}/**`]:'allow',[realPlugin]:'allow',[`${realPlugin}/**`]:'allow'}:'deny';
  const config={provider:{[provider]:original.provider[provider]},model,autoupdate:false,share:'disabled',
    plugin:[`file://${isolationPlugin}`,...(options.judge?[`file://${gradePlugin}`]:[]),...(plugin?[`file://${path.join(plugin,'opencode/plugin.js')}`]:[])],
    agent:{evaluate:{mode:'primary',description:'Run the supplied task in its isolated project',temperature:0,steps:40,
      permission:{'*':'allow',external_directory:externalAccess,task:'deny',webfetch:'deny',websearch:'deny',question:options.judge?'deny':'allow',edit:options.judge?'deny':'allow',bash:options.judge?'deny':'allow'}}},default_agent:'evaluate'};
  await fs.writeFile(path.join(configHome,'opencode/opencode.json'),JSON.stringify(config),{mode:0o600});
  const sourceAuth=path.join(os.homedir(),'.local/share/opencode/auth.json');
  try { const auth=JSON.parse(await fs.readFile(sourceAuth,'utf8'));await fs.writeFile(path.join(dataHome,'opencode/auth.json'),JSON.stringify({[provider]:auth[provider]}),{mode:0o600}); } catch(error) { if(error.code!=='ENOENT')throw error; }
  await fs.mkdir(bin,{recursive:true});
  const stub='#!/bin/sh\ncase "$1" in\n build) echo "SYNTHETIC FIXTURE: build command accepted; no SDK compilation or device verification performed."; exit 0;;\n device) echo "[]"; exit 0;;\n *) echo "SYNTHETIC FIXTURE: no SDK, document service, emulator or physical device is available."; exit 2;;\nesac\n';
  for(const command of ['devecocli','hdc','flutter'])await fs.writeFile(path.join(bin,command),stub,{mode:0o755});
  const env={...process.env,XDG_CONFIG_HOME:configHome,XDG_DATA_HOME:dataHome,XDG_STATE_HOME:path.join(root,'state'),XDG_CACHE_HOME:path.join(root,'cache'),OPENCODE_DISABLE_DEFAULT_PLUGINS:'true',OPENCODE_DISABLE_EXTERNAL_SKILLS:'true',OPENCODE_DISABLE_CLAUDE_CODE:'true',OPENCODE_DISABLE_AUTOUPDATE:'true',OPENCODE_DISABLE_PROJECT_CONFIG:'true',PATH:`${bin}:${process.env.PATH}`,PYTHONDONTWRITEBYTECODE:'1'};
  for(const key of ['OPENCODE_CONFIG','OPENCODE_CONFIG_CONTENT','OPENCODE_CONFIG_DIR','OPENCODE_SERVER_PASSWORD','OPENCODE_SERVER_USERNAME'])delete env[key];
  return {env,workspace};
}

export async function startServer({env,workspace}) {
  const child=spawn('opencode',['serve','--hostname','127.0.0.1','--port','0'],{cwd:workspace,env,stdio:['ignore','pipe','pipe']});
  let output='',base;
  const started=Date.now();
  child.stdout.on('data',chunk=>{output+=chunk;const match=output.match(/https?:\/\/127\.0\.0\.1:\d+/);if(match)base=match[0];});
  child.stderr.on('data',()=>{});
  let spawnError;child.on('error',error=>{spawnError=error;});
  while(!base){if(spawnError)throw spawnError;if(child.exitCode!==null||Date.now()-started>30000){child.kill();throw new Error('OpenCode server failed to start');}await delay(100);}
  const request=async(route,method='GET',body)=>{
    const response=await fetch(base+route,{method,headers:{'content-type':'application/json','x-opencode-directory':workspace},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
    if(!response.ok)throw new Error(`OpenCode ${method} ${route}: HTTP ${response.status} ${(await response.text()).slice(0,500)}`);
    const text=await response.text();return text?JSON.parse(text):null;
  };
  return {base,request,close:async()=>{child.kill('SIGTERM');await Promise.race([new Promise(resolve=>child.once('exit',resolve)),delay(2000)]);if(child.exitCode===null)child.kill('SIGKILL');}};
}

export async function executeSession(server,{prompt,model,timeoutSeconds=360,boundary=false,maxQuestions=4,onEvent,onProgress,judge=false,fixedAnswers}) {
  const health=await server.request('/global/health');
  if(health.version!=='1.18.29')throw new Error(`Expected OpenCode 1.18.29, received ${health.version}`);
  const session=await server.request('/session','POST',{title:judge?'Anonymous evaluation':'Plugin task evaluation'});
  const [providerID,...parts]=model.split('/');
  await server.request(`/session/${session.id}/prompt_async`,'POST',{model:{providerID,modelID:parts.join('/')},agent:'evaluate',parts:[{type:'text',text:prompt}]});
  const started=Date.now(), questions=[],seen=new Set();let status='completed',messages=[],error,progressKey;
  try { while(true){
    if(Date.now()-started>timeoutSeconds*1000){status='timeout';await server.request(`/session/${session.id}/abort`,'POST').catch(()=>{});break;}
    const asks=await server.request('/question');
    for(const ask of asks.filter(a=>a.sessionID===session.id&&!seen.has(a.id))){
      seen.add(ask.id);questions.push(ask);onEvent?.({type:'question',questions:ask.questions});
      if(questions.length>maxQuestions){status='question_limit';await server.request(`/question/${ask.id}/reject`,'POST');await server.request(`/session/${session.id}/abort`,'POST');break;}
      const answer=boundary?fixedAnswers.boundary:fixedAnswers.ordinary;
      ask.fixedAnswer=answer;
      await server.request(`/question/${ask.id}/reply`,'POST',{answers:ask.questions.map(()=>[answer])});
    }
    if(status!=='completed')break;
    messages=await server.request(`/session/${session.id}/message`);
    const assistants=messages.filter(m=>m.info.role==='assistant');
    const last=assistants.at(-1);
    const nextKey=`${messages.length}:${last?.info.time?.completed??0}:${last?.parts.filter(p=>p.type==='tool'&&p.state?.status==='completed').length??0}`;
    if(onProgress&&nextKey!==progressKey){progressKey=nextKey;await onProgress({sessionId:session.id,elapsedMs:Date.now()-started,questions,messages});}
    const states=await server.request('/session/status');
    if(last?.info.error){status='model_error';break;}
    if(judge&&messages.some(m=>m.parts.some(p=>p.type==='tool'&&p.tool==='submit_grade'&&p.state?.status==='completed'))){
      await server.request(`/session/${session.id}/abort`,'POST').catch(()=>{});break;
    }
    if(last?.info.time?.completed && (!states[session.id] || states[session.id].type==='idle') && ['stop','end_turn'].includes(last.info.finish))break;
    // Some providers report an idle final response without a finish reason.
    if(last?.info.time?.completed && (!states[session.id] || states[session.id].type==='idle') && last.parts.some(p=>p.type==='text') && !last.parts.some(p=>p.type==='tool'))break;
    await delay(400);
  }
  } catch(failure) {
    status='environment_error';error=failure.message;
    await server.request(`/session/${session.id}/abort`,'POST').catch(()=>{});
  }
  messages=await server.request(`/session/${session.id}/message`).catch(()=>messages);
  return {status,error,sessionId:session.id,elapsedMs:Date.now()-started,questions,messages};
}
