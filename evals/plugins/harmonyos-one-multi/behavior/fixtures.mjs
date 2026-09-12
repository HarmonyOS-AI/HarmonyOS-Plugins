import fs from 'node:fs/promises';
import path from 'node:path';

export const pagePath = (id) => `entry/src/main/ets/pages/${id}.ets`;
const json = (value) => JSON.stringify(value, null, 2) + '\n';
const page = (id, fixed = true) => `@Entry\n@Component\nstruct ${id} {\n  build() {\n    Column() {\n      Text('${id} 商品详情').fontSize(24)\n      Row() { Text('商品名称与价格说明').layoutWeight(1) }.width(${fixed ? '360' : "'100%'"})\n      Button('购买').id('${id}-buy')\n    }.width('100%').height('100%').expandSafeArea([SafeAreaType.SYSTEM], [SafeAreaEdge.BOTTOM])\n  }\n}\n`;

function workflowData(resumed, changedScope) {
  const pages = Object.fromEntries(['B01', 'B02'].map((id) => [pagePath(id), {
    type: 'detail-page', module: 'entry', dependencies: [], batchId: id, missingFromScan: false,
  }]));
  const issues = ['B01', 'B02'].map((id) => ({
    issueId: `${id}-UI-001`, batchId: id, page: pagePath(id), component: id,
    domain: 'size-layout', affectedPages: [], targetForms: ['phone', 'tablet'],
    problem: 'Row 固定为 360vp，窄窗溢出且宽窗不能自适应', source: 'task_analysis',
    rootCause: changedScope && id === 'B01' ? '宽度由公共 SharedLayout.ets 中的常量控制' : 'Row 使用固定宽度',
    proposal: changedScope && id === 'B01' ? '需要修改 entry/src/main/ets/common/SharedLayout.ets 的公共宽度，并回归两个消费者' : "将本页 Row 的 width(360) 改为容器可用宽度，保留业务和 id",
    plannedFiles: changedScope && id === 'B01' ? [pagePath(id), 'entry/src/main/ets/common/SharedLayout.ets'] : [pagePath(id)],
    verificationPlan: ['phone', 'tablet'].map((form) => ({form, checkId: 'row-width', routeId: `R-${id}`, check: '目标窗口 Row 不溢出，按钮仍可操作'})),
    changeStatus: resumed && id === 'B01' ? 'modified' : 'pending',
    verificationResults: resumed && id === 'B01' ? ['phone','tablet'].map((form) => ({form, checkId:'row-width', status:'not_verified', reason:'device_unavailable'})) : [],
    changedFiles: resumed && id === 'B01' ? [pagePath(id)] : [],
    changeSummary: resumed && id === 'B01' ? 'Row 已消费容器宽度；无设备，运行未验证' : null,
    notChangedReason: null, introducedByBatch: null, deferredRegressions: [],
  }));
  return {
    schemaVersion: 3,
    task: {taskId:'fixture-task', scope:Object.keys(pages), targetForms:['phone','tablet'], confirmationMode:'aggregate', routeMap:'output/route-map.json', status:resumed ? 'executing':'planning', currentBatch:resumed ? 'B02':'B01'},
    decisions: [{decisionId:'D-PRIOR', by:'user', summary:'不生成高保真，只做基础检查', reason:'用户之前明确选择', scope:[], conflictsWith:[], createdAt:'2026-09-01T00:00:00Z'}],
    pages,
    batches: ['B01','B02'].map((id) => ({batchId:id, pages:[pagePath(id)], dependencies:[], predecessors:id==='B02'?['B01']:[], domains:['size-layout'], risk:'low', status:resumed&&id==='B01'?'completed':'pending', specConfirmed:resumed&&id==='B01', testConclusion:'not_run'})),
    issues,
  };
}

export async function installFixture(directory, kind, plugin) {
  const files = {'AGENTS.md':'这是用于评测的合成源码工程。devecocli 是明确的测试桩，只能证明脚本流程可执行，不能证明 SDK 编译、设备运行或视觉正确。无需安装工具、依赖或联网查资料；只在本工程工作。用户指令决定是否修改源码。\n'};
  if (['arkui','workflow','resume','scope-change','web-host','hybrid'].includes(kind)) {
    Object.assign(files, {
      'build-profile.json5':json({app:{products:[{name:'default',compileSdkVersion:'5.0.0(12)'}]},modules:[{name:'entry',srcPath:'./entry'}]}),
      'oh-package.json5':json({name:'fixture',version:'1.0.0'}),
      'entry/src/main/module.json5':json({module:{name:'entry',type:'entry',srcEntry:'./ets/entryability/EntryAbility.ets',deviceTypes:['phone','tablet'],pages:'$profile:main_pages',routerMap:'$profile:router_map',abilities:[{name:'EntryAbility',srcEntry:'./ets/entryability/EntryAbility.ets',exported:true}]}}),
      'entry/src/main/resources/base/profile/main_pages.json':json({src:['pages/B01','pages/B02']}),
      'entry/src/main/resources/base/profile/router_map.json':json({routerMap:[{name:'Details',pageSourceFile:'src/main/ets/pages/B02.ets',buildFunction:'DetailsBuilder'}]}),
      'entry/src/main/ets/entryability/EntryAbility.ets':"import { UIAbility } from '@kit.AbilityKit';\nexport default class EntryAbility extends UIAbility {}\n",
      [pagePath('B01')]:page('B01',kind!=='resume'), [pagePath('B02')]:page('B02'),
    });
  }
  if (['workflow','resume','scope-change'].includes(kind)) {
    const om=path.join(directory,'.onemulti');
    await fs.mkdir(om,{recursive:true});
    for (const item of ['SKILL.md','scripts','references','assets']) await fs.cp(path.join(plugin,'skills/harmonyos-workflow-multi',item),path.join(om,item),{recursive:true});
    files['.onemulti/decisions.json']=json(workflowData(kind==='resume',kind==='scope-change'));
    files['.onemulti/evidence/index.json']=json({schemaVersion:3,taskId:'fixture-task',entries:[]});
      files['.onemulti/output/route-map.json']=json({schemaVersion:1,routes:['B01','B02'].map((id)=>({routeId:`R-${id}`,batchId:id,targetPage:pagePath(id),steps:[{stepId:'S01',action:'launch',desc:'启动应用，进入目标页面',target:'entry/EntryAbility',expectPage:id}]})),unresolved:[]});
    if(kind==='resume') files['.onemulti/adaptation-report-B01.html']='<html lang="zh"><body>B01 已修改 Row；设备未验证。</body></html>\n';
    if(kind==='scope-change') {
      files['entry/src/main/ets/common/SharedLayout.ets']='export const CONTENT_WIDTH: number = 360;\n';
      files[pagePath('B01')]="import { CONTENT_WIDTH } from '../common/SharedLayout';\n"+page('B01').replace('.width(360)','.width(CONTENT_WIDTH)');
    }
  }
  if (['web','hybrid'].includes(kind)) files['web/index.html']=kind==='web'
    ? '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>body { margin:0; min-width: 900px; } .cards { display:flex; flex-wrap:wrap } article { flex:1 1 15rem; min-width:0 }</style></head><body><main class="cards"><article><h1>新闻</h1><p>新闻详情</p><button id="save">收藏</button></article></main></body></html>\n'
    : '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><input id="name"><script>function refreshRem(){document.documentElement.style.fontSize=document.documentElement.clientWidth/10+"px";} refreshRem(); window.addEventListener("hostWindowChanged",function(){ console.log("window changed"); });</script></body></html>\n';
  if(['web-host','hybrid'].includes(kind)) files['entry/src/main/ets/pages/WebPage.ets']=`import { webview } from '@kit.ArkWeb';\n@Component\nstruct WebPage {\n private controller: webview.WebviewController = new webview.WebviewController();\n onWindowSizeChanged() { this.controller.runJavaScript("window.dispatchEvent(new Event('hostWindowChanged'))"); }\n build() { Web({ src: ${kind==='hybrid'?"$rawfile('index.html')":"'https://example.invalid/page'"}, controller: this.controller }).width(${kind==='web-host'?'360':"'100%'"}).height('100%') }\n}\n`;
  if(kind.startsWith('flutter')) {
    files['pubspec.yaml']=`name: fixture\nenvironment:\n  sdk: '>=3.0.0 <4.0.0'\ndependencies:\n  flutter:\n    sdk: flutter\n${kind==='flutter-hadss'?'  hadss_adaptive_layout: any\n':''}`;
    files['lib/main.dart']="import 'package:flutter/material.dart';\nvoid main() => runApp(const MaterialApp(home: ProductPage()));\nclass ProductPage extends StatefulWidget { const ProductPage({super.key}); @override State<ProductPage> createState()=>_ProductPageState(); }\nclass _ProductPageState extends State<ProductPage> { final scroll = ScrollController(); @override void dispose(){ scroll.dispose(); super.dispose(); } @override Widget build(BuildContext context) => Scaffold(body: Center(child:SizedBox(width:360, child:ListView(controller:scroll, children:const [Text('商品'), TextField()])))); }\n";
  }
  if(kind==='type-error')files['type-error.ts']='const count: number = 3;\nconst label: string = count;\n';
  if(kind==='camera')Object.assign(files,{
    'CameraFrames.ets':'// ImageReceiver 收到的帧 width=640，rowStride=672；每次会调用 image.release()。\nfunction copyRows(source: Uint8Array, width: number, height: number, rowStride: number): Uint8Array {\n const output = new Uint8Array(width * height);\n output.set(source.subarray(0, width * height));\n return output;\n}\n',
    'CameraSwitch.ets':"import { camera } from '@kit.CameraKit';\nlet requestedPosition: camera.CameraPosition = camera.CameraPosition.CAMERA_POSITION_FRONT;\nfunction selectCamera(supportedCameras: camera.CameraDevice[]): camera.CameraDevice { return supportedCameras[0]; }\n// supportedCameras 是 foldStatusChange 返回的当前能力快照；前置 ID 在折展后变化。\n",
  });
  for(const [name,content] of Object.entries(files)){ const full=path.join(directory,name);await fs.mkdir(path.dirname(full),{recursive:true});await fs.writeFile(full,content); }
}
