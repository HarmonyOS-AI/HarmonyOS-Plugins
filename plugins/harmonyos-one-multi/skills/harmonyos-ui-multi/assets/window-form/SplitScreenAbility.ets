/**
 * 拆分说明：参考示例 SplitScreenExample.ets 把 UIAbility 与两个 @Entry 页面塞进同一个文件，
 * 而 ArkTS 规定「一个文件只能有一个 @Entry」——原文件无法编译。
 * 收编时按职责拆成三个文件，内容未改。
 */

/**
 * 案例对照：图片设置固定大小，分屏场景下页面图片显示截断 vs 通过断点的变化来调整图片尺寸，在分屏下正常显示
 *
 * 场景：分屏模式下应用界面出现图片截断等问题
 * 根因：页面未根据断点动态调整布局和设置小窗口布局。
 *
 * 下面分别是正确案例（goodcase）和错误案例（badcase）
 */

// ==================== 正确案例（goodcase）====================
// 关键点：根据断点动态调整图片大小，避免小窗口显示不全而截断
// 效果：小窗下图片缩小，页面正常展示图片

// src/main/ets/entryability/EntryAbility.ets
import { AbilityConstant, ConfigurationConstant, UIAbility, Want } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { window } from '@kit.ArkUI';

const DOMAIN = 0x0000;

export default class EntryAbility extends UIAbility {
  private mainWindow?: window.Window;
  private sizeChangeCallback?: (size: window.Size) => void;

  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    try {
      this.context.getApplicationContext().setColorMode(ConfigurationConstant.ColorMode.COLOR_MODE_NOT_SET);
    } catch (err) {
      hilog.error(DOMAIN, 'testTag', 'Failed to set colorMode. Cause: %{public}s', JSON.stringify(err));
    }
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onCreate');
  }

  onDestroy(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onDestroy');
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    // Main window is created, set main page for this ability
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onWindowStageCreate');

    windowStage.loadContent('pages/Index', (err) => {
      try {
        // getMainWindowSync 必须在 loadContent 回调内取，之前拿到的是 0×0 的窗口
        this.mainWindow = windowStage.getMainWindowSync();
        const mainWindow = this.mainWindow;
        // 保存回调引用，onWindowStageDestroy 里按引用注销；
        // 裸 off('windowSizeChange') 会连带摘掉其他组件注册的监听
        this.sizeChangeCallback = (windowSize: window.Size) => {
          AppStorage.setOrCreate('WidthBreakpoint', mainWindow.getUIContext().getWindowWidthBreakpoint());
          AppStorage.setOrCreate('HeightBreakpoint', mainWindow.getUIContext().getWindowHeightBreakpoint());
        };
        mainWindow.on('windowSizeChange', this.sizeChangeCallback);
      } catch (error) {
        hilog.error(DOMAIN, 'testTag', 'Failed to register windowSizeChange. Cause: %{public}s',
          JSON.stringify(error));
      }
      if (err.code) {
        hilog.error(DOMAIN, 'testTag', 'Failed to load the content. Cause: %{public}s', JSON.stringify(err));
        return;
      }
      hilog.info(DOMAIN, 'testTag', 'Succeeded in loading the content.');
    });
  }

  onWindowStageDestroy(): void {
    // Main window is destroyed, release UI related resources
    if (this.mainWindow && this.sizeChangeCallback) {
      this.mainWindow.off('windowSizeChange', this.sizeChangeCallback);
    }
    this.mainWindow = undefined;
    this.sizeChangeCallback = undefined;
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onWindowStageDestroy');
  }

  onForeground(): void {
    // Ability has brought to foreground
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onForeground');
  }

  onBackground(): void {
    // Ability has back to background
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onBackground');
  }
}

// src/main/ets/pages/Index.ets
