/**
 * 示例：顺序前缀型组件的 displayPriority 逐项递减权重 —— 进度条/流程条按业务顺序截断
 *
 * 场景：流程进度条（节点 + 箭头连接符）随窗口变窄按显示价值裁剪，
 * 任意宽度下可见节点必须是业务顺序的连续前缀，且不残留孤立箭头
 *
 * 关键点：
 *   1. 权重粒度匹配断点位置：档位共用权重只能在档边界断开；进度条这类顺序前缀型
 *      组件按业务顺序逐项赋单调递减权重（KEEP_ORDER 序号取倒序），断点可以落在任何项上
 *   2. 先按各目标形态的容器宽度预算估算每形态显示到哪一项；最宽形态截断点之后的项
 *      （本例末位项）与更低档（基础项）合并同权——同一权重整组同时隐藏，
 *      比让末档项独占一档更稳
 *   3. 连接符权重取 min(前后节点权重)：任一端隐藏，箭头同步隐藏
 *   4. ForEach 交给完整数据集，不预裁；显隐数量由布局引擎决定
 *   5. 节点配 flexShrink(0)：可见时必须完整显示；外层 Row 提供 width('100%') 主轴约束
 *   6. 权重在组件渲染时由纯函数按 id 现算（静态可核验）；不要放进构造函数默认参数
 *      之类的间接层——运行时被抹平成同值后所有节点同组，引擎一个都不隐藏
 *
 * 不监听窗口或组件宽度，不计算可见数量，不预裁数据。
 *
 * 流程类组件（进度条/步骤条）通用示例；样式常量内联为独立可读的字面量，
 * 接入业务工程时替换回工程 token 与数据源。
 */

// ---- 内联样式常量 ----
const CHIP_HEIGHT: number = 32
const RADIUS_CHIP: number = 16
const SPACE_LG: number = 12
const SPACE_XL: number = 16
const FULL_SIZE: string = '100%'
const FONT_SIZE_CAPTION: number = 12
const COLOR_FONT_PRIMARY: string = '#FF182431'
const COLOR_FONT_TERTIARY: string = '#FF990033'
const COLOR_COMPONENT_BACKGROUND_SECONDARY: string = '#FFF1F3F5'

// ---- 内联数据模型（流程节点）----
interface FlowNode {
  id: string
  label: string
}

const FLOW_NODES: FlowNode[] = [
  { id: 'arrange', label: '下单' },
  { id: 'confirm', label: '确认' },
  { id: 'payment', label: '支付' },
  { id: 'stock', label: '备货' },
  { id: 'package', label: '打包' },
  { id: 'dispatch', label: '出库' },
  { id: 'transit', label: '运输' },
  { id: 'transfer', label: '中转' },
  { id: 'deliver', label: '派送' },
  { id: 'notify', label: '通知' },
  { id: 'sign', label: '签收' },
  { id: 'invoice', label: '开票' },
  { id: 'archive', label: '归档' },
  { id: 'review', label: '评价' }
]

// 基础价值常量：未列入 KEEP_ORDER 的扩展项与最宽形态放不下的末档项统一落在此档，
// 同权整组隐藏
const VISIBILITY_WEIGHT_BASE: number = 1

// 业务顺序（显示价值从高到低）：前 4 项关键 > 其后 4 项高 > 再 3 项中 > 末档低价值。
// 按序号倒序赋值得到逐项递减权重；末位项落到与基础项同权（11 项 - 下标 10 = 1），
// 最宽形态放不下时随基础项整组隐藏
const FLOW_KEEP_ORDER: string[] = [
  'arrange', 'confirm', 'payment', 'stock',
  'dispatch', 'package', 'transit', 'transfer', 'notify', 'deliver', 'sign'
]  // 上行 11 项为业务顺序，表外（invoice/archive/review）为基础档

function visibilityWeightForNode(nodeId: string): number {
  const index = FLOW_KEEP_ORDER.indexOf(nodeId)
  if (index < 0) {
    return VISIBILITY_WEIGHT_BASE
  }
  return FLOW_KEEP_ORDER.length - index
}

// 连接符权重 = min(前后节点权重)：任一端隐藏，箭头同步隐藏，不残留孤立箭头
function arrowWeight(nodes: FlowNode[], index: number): number {
  if (index + 1 >= nodes.length) {
    return visibilityWeightForNode(nodes[index].id)
  }
  return Math.min(
    visibilityWeightForNode(nodes[index].id),
    visibilityWeightForNode(nodes[index + 1].id)
  )
}

@ComponentV2
export struct FlowProgressTrack {
  @Require @Param nodes: FlowNode[] = FLOW_NODES

  build() {
    Row({ space: SPACE_LG }) {
      ForEach(this.nodes, (item: FlowNode, index: number) => {
        Text(item.label)
          .id(`flow-${item.id}`)
          .fontSize(FONT_SIZE_CAPTION)
          .fontColor(COLOR_FONT_PRIMARY)
          .maxLines(1)
          .textAlign(TextAlign.Center)
          .height(CHIP_HEIGHT)
          .padding({ left: SPACE_XL, right: SPACE_XL })
          .borderRadius(RADIUS_CHIP)
          .backgroundColor(COLOR_COMPONENT_BACKGROUND_SECONDARY)
          .flexShrink(0) // 可见时完整显示，不参与压缩
          .displayPriority(visibilityWeightForNode(item.id)) // 逐项递减：断点可落在任何项上

        if (index < this.nodes.length - 1) {
          Text('→')
            .id(`flow-${item.id}-arrow`)
            .fontSize(FONT_SIZE_CAPTION)
            .fontColor(COLOR_FONT_TERTIARY)
            .flexShrink(0)
            .displayPriority(arrowWeight(this.nodes, index))
        }
      }, (item: FlowNode) => item.id)
    }
    .id('flow-progress')
    .width(FULL_SIZE) // 主轴约束：displayPriority 按剩余空间触发显隐
    .height(CHIP_HEIGHT)
    .alignItems(VerticalAlign.Center)
    .clip(true) // 极限窄宽下兜底裁剪，避免隐藏过渡期间溢出视口
  }
}
