import fs from 'node:fs/promises';
import path from 'node:path';
import {writeJson} from './artifacts.mjs';
import {deterministicScore} from './score.mjs';
const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const rate=(passed,total)=>total?passed/total:0;

export function summarize(cases,records,judges,rubric){
 const runs=records.map(run=>{
  const test=cases.find(c=>c.id===run.caseId),machine=deterministicScore(test,run);
  const judge=judges.find(j=>j.caseId===run.caseId&&j.repetition===run.repetition);
  const key=Object.entries(judge?.mapping??{}).find(([,side])=>side===run.side)?.[0];
  const grade=judge?.grade?.[key];
  const semanticPass=!!grade&&grade.criteria.every(c=>c.pass)&&(!test.requireQuestion||grade.boundaryQuestion)&&(!Object.hasOwn(test,'maxRedundantQuestions')||grade.redundantQuestions<=test.maxRedundantQuestions);
  const critical=[...machine.critical,...(grade?.criticalErrors??[])];
  return {caseId:test.id,domain:test.domain,split:test.split,side:run.side,repetition:run.repetition,status:run.status,elapsedMs:run.elapsedMs,machine,grade,critical,pass:machine.pass&&semanticPass&&!critical.length,raw:`${run.side}-${run.caseId}-${run.repetition}.json`,judge:`judge-${run.caseId}-${run.repetition}.json`};
 });
 const metrics={};
 for(const side of ['baseline','candidate']){
  const selected=runs.filter(r=>r.side===side),workflow=selected.filter(r=>r.domain==='workflow');
  const authorized=selected.filter(r=>['workflow-continuous','workflow-aggregate','workflow-preferences','workflow-resume'].includes(r.caseId));
  const domains=Object.fromEntries([...new Set(cases.map(c=>c.domain))].map(d=>{const rows=selected.filter(r=>r.domain===d);return[d,{passed:rows.filter(r=>r.pass).length,total:rows.length,rate:rate(rows.filter(r=>r.pass).length,rows.length)}];}));
  const consistency=cases.map(c=>{const rows=selected.filter(r=>r.caseId===c.id);return{caseId:c.id,outcomes:rows.map(r=>r.pass),consistent:rows.length===2&&rows[0].pass===rows[1].pass};});
  metrics[side]={passed:selected.filter(r=>r.pass).length,total:selected.length,successRate:rate(selected.filter(r=>r.pass).length,selected.length),targetSuccessRate:rate(workflow.filter(r=>r.pass).length,workflow.length),redundantQuestions:authorized.reduce((n,r)=>n+(r.grade?.redundantQuestions??0),0),criticalErrors:selected.reduce((n,r)=>n+r.critical.length,0),environmentFailures:selected.filter(r=>['environment_error','model_error'].includes(r.status)).length,timeouts:selected.filter(r=>r.status==='timeout').length,domains,consistency};
 }
 const b=metrics.baseline,c=metrics.candidate;
 const targetDelta=c.targetSuccessRate-b.targetSuccessRate;
 const reduction=b.redundantQuestions>0?1-c.redundantQuestions/b.redundantQuestions:0;
 const regressions=runs.filter(r=>r.side==='candidate'&&!r.pass&&runs.some(b=>b.side==='baseline'&&b.caseId===r.caseId&&b.repetition===r.repetition&&b.pass)).map(r=>({caseId:r.caseId,repetition:r.repetition}));
 const gates={completeSample:runs.length===80&&judges.length===40&&judges.every(j=>!!j.grade&&!j.error),candidateAtLeast90:c.successRate>=rubric.successRateMinimum,notBelowBaseline:c.successRate>=b.successRate,targetImprovement:targetDelta>=rubric.successRateDelta||reduction>=rubric.redundantQuestionReduction,zeroCritical:c.criticalErrors===0,domainsNotRegressed:Object.keys(c.domains).filter(d=>d!=='workflow').every(d=>c.domains[d].rate>=b.domains[d].rate)};
 return {metrics,targetDelta,redundantQuestionReduction:reduction,gates,qualityImproved:false,regressions,runs,judgeFailures:judges.filter(j=>j.error).map(j=>({caseId:j.caseId,repetition:j.repetition,error:j.error}))};
}

export async function writeReport(outputRoot,summary,configuration,deterministic){
 summary.gates.deterministic=deterministic.candidate.exitCode===0&&deterministic.candidate.brokenLinks.length===0;
 summary.qualityImproved=Object.values(summary.gates).every(Boolean);
 const data={...summary,configuration,deterministic,limitations:['20 个合成场景，每版每场景仅 2 次；小样本不能外推为全面质量证明。','构建、设备与文档命令为显式测试桩，未进行真实 SDK 编译或真机验证。','同一模型进行匿名配对评分仍可能有裁判偏差，原始轨迹与证据引用保留供人工复核。','服务会话和配置隔离；工具权限与宿主依赖固定，但没有操作系统级沙箱。','超时、环境故障及评分失败保留，不从成功率分母静默移除。']};
 await writeJson(path.join(outputRoot,'comparison.json'),data);
 const pct=n=>`${(n*100).toFixed(1)}%`;
 const metrics=['passed','total','successRate','targetSuccessRate','redundantQuestions','criticalErrors','environmentFailures','timeouts'];
 const labels={passed:'成功任务',total:'任务总数',successRate:'任务成功率',targetSuccessRate:'Workflow 目标成功率',redundantQuestions:'已授权场景冗余确认',criticalErrors:'严重错误',environmentFailures:'环境/模型故障',timeouts:'任务超时'};
 const rows=metrics.map(key=>`<tr><th>${labels[key]}</th>${['baseline','candidate'].map(side=>`<td>${key.endsWith('Rate')?pct(data.metrics[side][key]):data.metrics[side][key]}</td>`).join('')}</tr>`).join('');
 const details=data.runs.map(run=>`<tr><td>${escape(run.caseId)}<small>${run.split} · #${run.repetition+1}</small></td><td>${run.side}</td><td class="${run.pass?'pass':'fail'}">${run.pass?'通过':'未通过'}</td><td>${Math.round((run.elapsedMs??0)/1000)} s</td><td><details><summary>判断与证据</summary><pre>${escape(JSON.stringify({machine:run.machine.checks.filter(c=>!c.pass),grade:run.grade,critical:run.critical},null,2))}</pre></details><a href="${run.raw}">原始执行</a> · <a href="${run.judge}">匿名评分</a></td></tr>`).join('');
 const html=`<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>一多 P1 前后对比评测</title><style>body{font:16px/1.6 system-ui;margin:0;background:#f4f6f8;color:#152336}main{max-width:1200px;margin:auto;padding:32px}h1{font-size:30px}table{border-collapse:collapse;width:100%;background:white;margin:20px 0}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #dbe1e7}small{display:block;color:#64748b}.pass{color:#087a4a}.fail{color:#b53125}.banner{padding:22px;background:white;border-left:5px solid ${data.qualityImproved?'#087a4a':'#b53125'}}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:500px;overflow:auto}a{color:#245da7}code{overflow-wrap:anywhere}</style><main><h1>一多插件 P1 · 前后对比</h1><div class="banner"><strong>${data.qualityImproved?'达到本轮质量提升门槛':'尚未达到本轮质量提升门槛'}</strong><p>固定模型 ${escape(configuration.model)} · OpenCode ${escape(configuration.opencodeVersion)} · 80 次计划任务 + 40 次计划盲评</p></div><p><a href="comparison.json">JSON 明细</a> · <a href="configuration.json">版本与配置</a> · <a href="deterministic.json">确定性对比</a></p><table><tr><th>指标</th><th>修改前</th><th>修改后</th></tr>${rows}</table><h2>验收门槛</h2><pre>${escape(JSON.stringify(data.gates,null,2))}</pre><h2>两次运行一致性及退化</h2><pre>${escape(JSON.stringify({consistency:Object.fromEntries(['baseline','candidate'].map(s=>[s,data.metrics[s].consistency])),regressions:data.regressions,judgeFailures:data.judgeFailures},null,2))}</pre><h2>确定性回归</h2><pre>${escape(JSON.stringify(deterministic,null,2))}</pre><h2>逐次任务证据</h2><table><tr><th>场景</th><th>版本</th><th>结果</th><th>用时</th><th>证据</th></tr>${details}</table><h2>范围与局限</h2><ul>${data.limitations.map(x=>`<li>${escape(x)}</li>`).join('')}</ul><h2>复现</h2><pre>npm run evals:one-multi:history
npm run evals
npm run evals:one-multi:compare -- --output ${escape(outputRoot)}</pre></main></html>`;
 await fs.writeFile(path.join(outputRoot,'comparison.html'),html);
 return data;
}
