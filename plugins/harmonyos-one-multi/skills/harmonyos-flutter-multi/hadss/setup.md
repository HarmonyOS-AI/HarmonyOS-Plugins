# HADSS 接入

先检查 `pubspec.yaml`、lockfile 和现有导入，确认包名、版本及当前 API。若未引入且用户允许新增依赖，给出基于工程实际包源的变更；无法确认版本时明确标记待查，不猜版本号。

应用级初始化和监听集中管理，页面只消费断点、FoldStatus 和 avoid area。所有 listener 在 `dispose` 中对称移除；保留原生 Flutter 降级路径只应出现在架构决策中，不在本目录混写其实现。
