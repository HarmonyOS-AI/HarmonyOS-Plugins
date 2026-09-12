import {transcript} from './artifacts.mjs';
import {pagePath} from './fixtures.mjs';

export function deterministicScore(test,run) {
 const checks=[],critical=[];
 const check=(id,pass,evidence)=>checks.push({id,pass:!!pass,evidence});
 check('execution-completed',run.status==='completed',run.status);
 check('plugin-unmodified',run.pluginChanged===false,run.sourceSha256);
 if(run.pluginChanged)critical.push({type:'outside-authorized-scope',evidence:['loaded plugin modified']});
 if(test.id==='workflow-ci-analysis')check('noninteractive-ci',run.questions.length===0,run.questions);
 const trace=transcript(run);
 const skillReads=new Set();
 for(const event of trace){
  if(event.type!=='tool'||event.status!=='completed')continue;
  if(event.tool==='harmonyos_one_multi_skill')skillReads.add(event.input.skill);
  const paths=JSON.stringify(event.input);
  for(const skill of [...(test.skills??[]),...(test.forbiddenSkills??[])])if(paths.includes(`${skill}/SKILL.md`))skillReads.add(skill);
 }
 for(const skill of test.skills??[])check(`read:${skill}`,skillReads.has(skill),[...skillReads]);
 for(const skill of test.forbiddenSkills??[])check(`avoid:${skill}`,!skillReads.has(skill),[...skillReads]);
 const business=run.changedFiles.filter(file=>!file.startsWith('.onemulti/')&&file!=='.gitignore');
 const allowed=new Set([...(test.allowedOutputs??[]),...(test.mustChange??[]),...(test.changedPages??[]).map(pagePath)]);
 // The hybrid prompt authorizes both existing ends; mustChange is a required
 // output, not an exclusive edit allowlist. Other pages remain outside scope.
 if(test.fixture==='hybrid')allowed.add('entry/src/main/ets/pages/WebPage.ets');
 const outside=business.filter(file=>!allowed.has(file));
 check('authorized-file-scope',outside.length===0,outside);
 if(outside.length)critical.push({type:test.readOnly?'analysis-business-write':'outside-authorized-scope',evidence:outside});
 if(test.noWorkflowState)check('no-workflow-state',!run.changedFiles.some(file=>file.startsWith('.onemulti/')),run.changedFiles);
 if(test.readOnly&&!test.requireQuestion)check('analysis-only-outputs',run.changedFiles.every(file=>(test.allowedOutputs??[]).includes(file)),run.changedFiles);
 for(const id of test.changedPages??[]){
  const file=pagePath(id),content=run.after[file]?.text??'';
  check(`repair:${id}`,run.changedFiles.includes(file)&&!content.includes('.width(360)')&&new RegExp(`\\.id\\(\\s*([\'\"])${id}-buy\\1\\s*\\)`).test(content),{file,sha256:run.after[file]?.sha256});
 }
 for(const id of test.untouchedPages??[])check(`preserve:${id}`,run.before[pagePath(id)]?.sha256===run.after[pagePath(id)]?.sha256,pagePath(id));
 for(const file of [...(test.mustChange??[]),...(test.allowedOutputs??[])])check(`output:${file}`,run.changedFiles.includes(file)&&run.after[file]?.bytes>0,file);
 if(test.domain==='workflow'&&test.changedPages){
  let ledger;try{ledger=JSON.parse(run.after['.onemulti/decisions.json']?.text??'null');}catch{}
  check('schema-v3-ledger',ledger?.schemaVersion===3,'after:.onemulti/decisions.json');
  const invented=(ledger?.issues??[]).flatMap(i=>(i.verificationResults??[]).filter(r=>r.status==='passed').map(r=>({issueId:i.issueId,...r})));
  check('no-invented-device-pass',invented.length===0,invented);
  if(invented.length)critical.push({type:'unsupported-runtime-success',evidence:invented});
  for(const id of test.changedPages){
   const issue=ledger?.issues?.find(i=>i.batchId===id);
   check(`ledger:${id}`,issue?.changeStatus==='modified'&&issue.changedFiles?.includes(pagePath(id)),issue);
   const report=Object.entries(run.after).find(([f,d])=>f.endsWith(`adaptation-report-${id}.html`)&&d.bytes>100);
   check(`report:${id}`,!!report,report?.[0]);
  }
  const existing=JSON.parse(run.before['.onemulti/decisions.json'].text);
  check('prior-decisions-preserved',existing.decisions.every(d=>ledger?.decisions?.some(n=>n.decisionId===d.decisionId)),existing.decisions.map(d=>d.decisionId));
  if(['workflow-continuous','workflow-aggregate','workflow-resume'].includes(test.id))check('summary-report',Object.entries(run.after).some(([f,d])=>f.endsWith('adaptation-summary.html')&&d.bytes>100),'after:.onemulti/adaptation-summary.html');
 }
 return {checks,critical,skillReads:[...skillReads],toolQuestions:run.questions.length,pass:checks.every(c=>c.pass)&&!critical.length};
}

// Preserve event IDs and useful evidence, while omitting full copied runtime libraries.
function visibleArtifact(file,text){
 if(!text)return text;
 if(file.endsWith('.html'))return text.replace(/<style[^]*?<\/style>|<script[^]*?<\/script>/gi,'').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').slice(0,16000);
 return text.slice(0,20000);
}
export function judgeEvidence(run){
 const events=transcript(run).map((event,index)=>{
  if(event.type==='text')return {id:`T${index}`,role:event.role,text:event.text};
  const resource=event.tool==='harmonyos_one_multi_skill'||/\.onemulti\/(scripts|references)|\.plugin\//.test(JSON.stringify(event.input));
  const limit=resource?500:3000;
  return {id:`T${index}`,tool:event.tool,input:JSON.stringify(event.input).slice(0,2500),status:event.status,output:(event.output??event.error??'').slice(0,limit)};
 });
 const artifacts=Object.fromEntries(run.changedFiles.filter(f=>!/^\.onemulti\/(scripts|references|assets)\//.test(f)&&f!=='.onemulti/SKILL.md').map(f=>[f,{before:run.before[f]?.text?.slice(0,2500),after:visibleArtifact(f,run.after[f]?.text)}]));
 return {status:run.status,events,artifacts};
}
