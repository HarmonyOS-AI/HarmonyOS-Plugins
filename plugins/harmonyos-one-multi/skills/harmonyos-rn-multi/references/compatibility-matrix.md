# RNOH 版本与兼容矩阵

不要把 API、prop 或生命周期写成永久事实。先读取项目 lockfile 和 Harmony 构建配置，再查对应版本 tag 的官方资料/源码；最新文档只可补充线索。

## 盘点顺序

1. 确认 workspace、JS 包管理器、Harmony 工程根和目标 SDK/API。
2. 读取 `package.json` 与实际 `package-lock/yarn.lock/pnpm-lock`，记录解析版本和来源。
3. 读取所有 `oh-package.json5`、`oh-package-lock.json5`、`build-profile.json5` 与 Hvigor 配置。
4. 查 `harmony.codegenConfig`、Codegen 脚本、Autolinking 输出、生成目录和 Package/Module/Component 注册。
5. 对每个疑似不兼容项读取对应 tag 的类型、实现、release notes 或官方样例，不读 master/latest 后直接抄 API。

## 项目矩阵

| 能力 | 声明版本 | 锁定/解析版本 | 证据来源 | 配套项 | 运行证据 | 风险/决策 |
| --- | --- | --- | --- | --- | --- | --- |
| React Native |  |  | package + lock | TS types |  |  |
| react-native-harmony |  |  | package + lock/HAR | CLI/template |  |  |
| RNOH CLI/Codegen |  |  | package + lock | generated bindings |  |  |
| Harmony HAR/SDK |  |  | oh-package/build profile | Host API |  |  |
| 导航/安全区/手势 |  |  | lock + Harmony 实现 | Autolinking |  |  |
| 原生 UI/其他布局库 |  |  | lock + package contents | registration |  |  |

版本不能只写“最新”“0.8x”或“兼容”。lockfile 无精确值时说明原因；库 README 与安装包不一致时，以当前安装内容和可复现构建为准并记录文档偏差。

## 三方库与 Codegen

- 检查 JS 包是否含 Harmony 平台入口、ArkTS/C-API/HAR，或是否要求独立 Harmony 包。
- 确认 Autolinking 是否支持当前版本与 monorepo；手工 Package 注册时记录 owner 和销毁路径。
- 没有 Harmony 实现时，不把 Android `.aar`、Java/Kotlin 或 iOS ObjC/Swift 代码当 HarmonyOS 修复。
- Codegen 闭环为：TS Spec → codegen config/tool → generated types/bindings → ArkTS/C-API 实现 → Package/Component 注册 → JS wrapper。
- 生成物可由锁定命令重建；不手改，不在多个输出目录残留旧版本。

## 决策

- **升级**：有对应修复证据、兼容线明确、迁移与回滚可控。
- **规避**：当前版本可局部规避且升级风险更大；记录删除规避的版本条件。
- **替代**：库无 Harmony 实现、维护/许可/能力不满足目标。
- **自研桥接**：能力必要、无等价实现，且 TurboModule/Fabric 选择与长期维护成本已确认。

验证按工程实际脚本依次执行依赖/Codegen、TypeScript、bundle、HAR/Hvigor 和目标设备路径。不可构建的历史基线单独记录，不能算作本次成功或失败。
