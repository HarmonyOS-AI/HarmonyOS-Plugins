# 多模态验证常见问题集合

本文件集中存放设备运行与图像验证中的常见问题及操作指导。它不定义批次边界、测试模式、轮次上限或结果聚合，只处理进入 L3 后的设备、安装、导航、形态、采集和临时产物问题。

## 真机到安装阶段发现签名不可用

**现象**：构建成功，但真机安装报告未配置签名、产物未签名、UDID 不匹配、不能安装 unsigned HAP，或返回错误码 `9568423`。

**原因**：构建成功不代表签名 profile 可以用于当前真机。

**操作：

1. 中断验证，保持已绑定真机、`stage=device_ready` 和当前轮次不变。
3. 向用户提供：
   - **已完成签名配置，继续验证**
   - **暂不配置签名，停止真机验证**
   - **其他**
4. 用户选择继续时，在同一真机、同一轮次重新执行安装；仍是签名错误则继续保持中断。

## HSP 工程先按单 HAP 安装

**现象**：普通入口 HAP 安装失败后，才发现应用依赖一个或多个 HSP，需要重新推包。

**原因**：安装前没有确认当前构建产物的 HAP/HSP 拓扑。

**操作**：

1. 存在 HSP 时，直接使用目录整体安装，不先尝试只安装入口 HAP。
4. 将示例文件名替换为本轮实际构建产物，并对每个依赖包执行一次 `hdc file send`：

```bash
hdc shell mkdir data/local/tmp/install_dir
hdc file send library-default-signed.hsp "data/local/tmp/install_dir"
hdc file send entry-default-signed.hap "data/local/tmp/install_dir"
hdc shell bm install -p "data/local/tmp/install_dir"
hdc shell rm -rf data/local/tmp/install_dir
```

安装后按真实 bundle、module 和 Ability 启动：

```bash
hdc shell aa start -a <AbilityName> -b <bundleName> -m <moduleName>
```

## 推包后启动了错误的应用包

**现象**：HAP/HSP 已成功安装，但启动失败、启动了另一个环境的应用，或按 `AppScope/app.json5` 中的包名找不到本轮构建出的应用。

**原因**：当前使用的签名由 product 的 `signingConfig` 指定；因此推包时只读取 `AppScope/app.json5`，可能忽略根目录 `build-profile.json5` 对包名的覆盖。

**操作**：

1. 读取根目录 `build-profile.json5`，在 `app.products[]` 中找到 `name` 等于当前 product 的配置，核对其 `signingConfig` 和 `bundleName`。
2. 当前 product 配置了非空 `bundleName` 时，以该值作为本轮真实包名。
3. 安装完成后，使用解析出的真实包名启动对应的 module 和 Ability：

```bash
hdc shell aa start \
  -a <AbilityName> \
  -b <bundleName-from-current-product> \
  -m <moduleName>
```

## 应用截图黑屏、缺失或受隐私保护

**现象**：应用可操作，但截图没有目标内容。

**原因**：截图页面为隐私模式页面。

**操作**：

1. 黑屏、透明、内容缺失或明确受保护时，检查 `setWindowPrivacyMode` 等窗口设置并等待用户决定是否临时关闭。
2. 用户不允许关闭时，将无法判断的 L3 项转为 `not_verified`；不要把无效截图写入正式 evidence。

## simplified 布局树找不到文本或可点击节点

**现象**：布局树中没有目标文本或节点，随后开始根据截图反复猜坐标。

**原因**：精简布局树可能过滤自绘组件、深层文本、完整 bounds 或可访问性信息。

**操作**：

先查看工具参数：

```bash
devecocli ui click --help
devecocli ui layout --help
```

导航定位需要组件树时直接获取完整模式：

```bash
devecocli ui layout --format json --mode full --depth 0 \
  > "$OM/evidence/tmp/<name>-component-tree.json"
```

定位顺序为：

1. 冻结 route-map 中可直接启动的页面或 Ability；
2. 既有组件 id；
3. 完整布局树中的文本、组件类型和可见状态；
4. 经过换算的 bounds 中心；
5. 仍不可用时请求人工操作。

图片用于视觉判断；组件树用于导航定位或图片无法完成的结构判断。正式组件树登记为 `type=component_tree`，并链接对应的 `issueId + form + checkId`。

## 截图、物理屏幕和布局树坐标不一致

**现象**：根据截图或布局树计算的点击位置没有命中，多次微调仍不稳定。

**原因**：混用了设备物理像素、截图尺寸、预览缩放尺寸和布局树坐标空间。

**操作**：

点击前记录：

```text
physicalSize
screenshotSize
layoutCoordinateSize
scaleX
scaleY
```

- 优先点击 id 或文本节点。
- 必须使用坐标时，将布局树 bounds 换算到设备输入坐标，再点击节点中心。
- 禁止根据缩放后的预览图片连续试点。
