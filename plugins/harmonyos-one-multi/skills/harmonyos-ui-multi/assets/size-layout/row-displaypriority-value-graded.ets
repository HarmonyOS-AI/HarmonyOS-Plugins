/**
 * 示例：按业务价值分级减少内容 —— 命名 displayPriority 权重 + 组容器整组显隐
 *
 * 场景：单行信息条（登机口 / 准点率 / 座位 / 附加服务 / 分享）随窗口变窄时，
 * 按业务价值从低到高逐级隐藏，而不是截断或挤压
 *
 * 关键点：
 *   1. 权重用命名常量表达价值层级（CRITICAL > HIGH > MEDIUM > LOW > BASE），不散落魔数；
 *      值越大越优先显示
 *   2. 同一价值层级共用同一权重：座位与分享同为 MEDIUM，宽度不足时同时显隐，
 *      不会在同级内从尾部逐项隐藏
 *   3. 附加服务的多个小项封装为一个 Row 组容器，displayPriority 设在组容器上整组
 *      显隐；组内子项不再单独设置 displayPriority
 *   4. 已设 displayPriority 的关键项配 flexShrink(0)：优先显示的项必须完整显示，
 *      不参与压缩
 *   5. 外层 Row 提供 width('100%') 主轴约束；显隐数量由布局引擎按子项实际测量
 *      尺寸和权重决定
 *
 * 不监听窗口或组件宽度，不计算可见数量，不预裁数据。
 *
 * 航班信息行示例；样式常量与数据模型在此内联为独立可读的字面量，
 * 接入业务工程时替换为工程 token 与数据源。
 */

// ---- 内联样式常量 ----
const CHIP_HEIGHT: number = 32
const MINI_CHIP_HEIGHT: number = 24
const RADIUS_CHIP: number = 16
const RADIUS_CARD: number = 12
const RADIUS_GROUP: number = 8
const SPACE_SM: number = 4
const SPACE_MD: number = 8
const SPACE_LG: number = 12
const SPACE_XL: number = 16
const FULL_SIZE: string = '100%'
const FONT_SIZE_TINY: number = 10
const FONT_SIZE_CAPTION: number = 12
const FONT_SIZE_LABEL: number = 14
const COLOR_FONT_PRIMARY: string = '#FF182431'
const COLOR_FONT_SECONDARY: string = '#FF666666'
const COLOR_COMPONENT_BACKGROUND_PRIMARY: string = '#FFFFFFFF'
const COLOR_COMPONENT_BACKGROUND_SECONDARY: string = '#FFF1F3F5'
const COLOR_COMPONENT_BACKGROUND_TERTIARY: string = '#FFE8EAED'

// ---- 内联数据模型 ----
interface FlightExtra {
  id: string
  label: string
}

interface FlightScene {
  infoRowId: string
  gateLabel: string
  gateValue: string
  onTimeLabel: string
  seatLabel: string
  shareLabel: string
  extras: FlightExtra[]
}

const FLIGHT_SCENE: FlightScene = {
  infoRowId: 'flight-info-row',
  gateLabel: '登机口',
  gateValue: 'C12',
  onTimeLabel: '准点率 98%',
  seatLabel: '45A 靠窗',
  shareLabel: '分享',
  extras: [
    { id: 'meal', label: '餐食' },
    { id: 'wifi', label: 'Wi-Fi' },
    { id: 'lounge', label: '休息室' }
  ]
}

// ---- 价值层级：命名权重常量，禁止在组件里散落魔数 ----
const VISIBILITY_WEIGHT_CRITICAL: number = 5
const VISIBILITY_WEIGHT_HIGH: number = 4
const VISIBILITY_WEIGHT_MEDIUM: number = 3
const VISIBILITY_WEIGHT_LOW: number = 2
const VISIBILITY_WEIGHT_BASE: number = 1

@ComponentV2
export struct FlightInfoRow {
  build() {
    Row({ space: SPACE_LG }) {
      Row({ space: SPACE_SM }) {
        Text(FLIGHT_SCENE.gateLabel)
          .fontSize(FONT_SIZE_TINY)
          .fontColor(COLOR_FONT_SECONDARY)
        Text(FLIGHT_SCENE.gateValue)
          .fontSize(FONT_SIZE_LABEL)
          .fontColor(COLOR_FONT_PRIMARY)
          .fontWeight(FontWeight.Bold)
      }
      .id('flight-gate-info')
      .height(CHIP_HEIGHT)
      .padding({ left: SPACE_XL, right: SPACE_XL })
      .borderRadius(RADIUS_CHIP)
      .backgroundColor(COLOR_COMPONENT_BACKGROUND_SECONDARY)
      .alignItems(VerticalAlign.Center)
      .flexShrink(0) // 登机口必须完整显示，不参与压缩
      .displayPriority(VISIBILITY_WEIGHT_CRITICAL) // 价值最高，最后被隐藏

      Text(FLIGHT_SCENE.onTimeLabel)
        .id('flight-ontime')
        .fontSize(FONT_SIZE_CAPTION)
        .fontColor(COLOR_FONT_PRIMARY)
        .maxLines(1)
        .textAlign(TextAlign.Center)
        .height(CHIP_HEIGHT)
        .padding({ left: SPACE_LG, right: SPACE_LG })
        .borderRadius(RADIUS_CHIP)
        .backgroundColor(COLOR_COMPONENT_BACKGROUND_SECONDARY)
        .flexShrink(0)
        .displayPriority(VISIBILITY_WEIGHT_HIGH)

      Text(FLIGHT_SCENE.seatLabel)
        .id('flight-seat')
        .fontSize(FONT_SIZE_CAPTION)
        .fontColor(COLOR_FONT_PRIMARY)
        .maxLines(1)
        .textAlign(TextAlign.Center)
        .height(CHIP_HEIGHT)
        .padding({ left: SPACE_LG, right: SPACE_LG })
        .borderRadius(RADIUS_CHIP)
        .backgroundColor(COLOR_COMPONENT_BACKGROUND_SECONDARY)
        .flexShrink(0)
        .displayPriority(VISIBILITY_WEIGHT_MEDIUM)

      // 附加服务整体是一个语义组：displayPriority 设在组容器上，整组显隐；
      // 组内 ForEach 的子项不单独设置 displayPriority，也不按宽度预裁 extras
      Row({ space: SPACE_SM }) {
        ForEach(FLIGHT_SCENE.extras, (extra: FlightExtra) => {
          Text(extra.label)
            .id(`flight-${extra.id}`)
            .fontSize(FONT_SIZE_CAPTION)
            .fontColor(COLOR_FONT_PRIMARY)
            .maxLines(1)
            .textAlign(TextAlign.Center)
            .height(MINI_CHIP_HEIGHT)
            .padding({ left: SPACE_LG, right: SPACE_LG })
            .borderRadius(RADIUS_CARD)
            .backgroundColor(COLOR_COMPONENT_BACKGROUND_PRIMARY)
            .flexShrink(0)
        }, (extra: FlightExtra) => extra.id)
      }
      .id('flight-extras')
      .height(CHIP_HEIGHT)
      .alignItems(VerticalAlign.Center)
      .padding({ left: SPACE_MD, right: SPACE_MD, top: SPACE_SM, bottom: SPACE_SM })
      .borderRadius(RADIUS_GROUP)
      .backgroundColor(COLOR_COMPONENT_BACKGROUND_TERTIARY)
      .flexShrink(0)
      .displayPriority(VISIBILITY_WEIGHT_LOW) // 价值最低，宽度不足时最先整组隐藏

      Text(FLIGHT_SCENE.shareLabel)
        .id('flight-share')
        .fontSize(FONT_SIZE_CAPTION)
        .fontColor(COLOR_FONT_PRIMARY)
        .maxLines(1)
        .textAlign(TextAlign.Center)
        .height(CHIP_HEIGHT)
        .padding({ left: SPACE_LG, right: SPACE_LG })
        .borderRadius(RADIUS_CHIP)
        .backgroundColor(COLOR_COMPONENT_BACKGROUND_SECONDARY)
        .flexShrink(0)
        .displayPriority(VISIBILITY_WEIGHT_MEDIUM) // 与座位同级：同时显示或隐藏
    }
    .id(FLIGHT_SCENE.infoRowId)
    .width(FULL_SIZE) // 主轴约束：displayPriority 按剩余空间触发显隐
    .height(CHIP_HEIGHT)
    .alignItems(VerticalAlign.Center)
    .justifyContent(FlexAlign.Start)
    .clip(true) // 极限窄宽下兜底裁剪，避免隐藏过渡期间溢出视口
  }
}
