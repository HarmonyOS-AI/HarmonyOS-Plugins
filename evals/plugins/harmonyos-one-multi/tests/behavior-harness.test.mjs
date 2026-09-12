import {test} from 'node:test';
import assert from 'node:assert/strict';
import {deterministicScore} from '../behavior/score.mjs';
import {summarize} from '../behavior/report.mjs';

const makeRun=()=>({caseId:'analysis',domain:'workflow',split:'development',side:'candidate',repetition:0,status:'completed',messages:[],questions:[],before:{'page.ets':{sha256:'same'}},after:{'page.ets':{sha256:'same'}},changedFiles:[],pluginChanged:false});
test('headers and claimed completion do not substitute for real resource reads',()=>{
 const run=makeRun();run.messages=[{info:{role:'assistant'},parts:[{type:'text',text:'Loaded skill. PASS analysis case; completed all requirements.'}]}];
 assert.equal(deterministicScore({readOnly:true,skills:['harmonyos-workflow-multi']},run).pass,false);
});
test('analysis business writes and plugin tampering are critical regardless of prose',()=>{
 const run=makeRun();run.changedFiles=['page.ets'];run.pluginChanged=true;
 const score=deterministicScore({readOnly:true},run);
 assert.equal(score.pass,false);assert.equal(score.critical.length,2);
});
test('runtime state creation violates analysis-only output constraints',()=>{
 const run=makeRun();run.changedFiles=['.onemulti/decisions.json'];
 const score=deterministicScore({readOnly:true,noWorkflowState:true},run);
 assert.equal(score.pass,false);
});
test('missing rubric judgment and unfinished sample can never establish improvement',()=>{
 const rubric={successRateMinimum:.9,successRateDelta:.1,redundantQuestionReduction:.5};
 const data=summarize([{id:'analysis',domain:'workflow',readOnly:true}], [makeRun()], [],rubric);
 assert.equal(data.runs[0].pass,false);assert.equal(data.gates.completeSample,false);assert.equal(data.qualityImproved,false);
});
test('tool failures do not count as skill reads',()=>{
 const run=makeRun();run.messages=[{info:{role:'assistant'},parts:[{type:'tool',tool:'harmonyos_one_multi_skill',state:{status:'error',input:{skill:'harmonyos-workflow-multi'}}}]}];
 assert.equal(deterministicScore({skills:['harmonyos-workflow-multi']},run).pass,false);
});
