# PlatformView 与 Channel 通信指南

本文档整合自 `flutter_samples/ohos/docs` 中的 PlatformView 和 Channel 文档。

## PlatformView (OhosView)

嵌入 OHos 原生视图（地图、相机、视频、传感器等）到 Flutter 页面。

### 架构：Plugin → Factory → Component 三层注册

```
FlutterPlugin (注册)
  └→ PlatformViewFactory (创建)
       └→ PlatformView (视图)
            └→ @Component (ArkUI 组件)
```

### Native 侧实现

#### 1. 定义 ArkUI Component

```typescript
@Component
struct ButtonComponent {
  @ObjectLink params: Params
  customView: CustomView = this.params.platformView as CustomView

  build() {
    Column() {
      Button("发送数据给Flutter")
        .onClick((event: ClickEvent) => {
          this.customView.sendMessage();
        })
      Text(`来自Flutter的数据: ${this.storageLink}`)
    }
    .width('100%')
    .height('100%')
  }
}

@Builder
function ButtonBuilder(params: Params) {
  ButtonComponent({ params: params })
}
```

#### 2. 实现 PlatformView

```typescript
import MethodChannel, { MethodCallHandler, MethodResult }
  from '@ohos/flutter_ohos/src/main/ets/plugin/common/MethodChannel';
import PlatformView, { Params }
  from '@ohos/flutter_ohos/src/main/ets/plugin/platform/PlatformView';

@Observed
export class CustomView extends PlatformView implements MethodCallHandler {
  methodChannel: MethodChannel;

  constructor(context: common.Context, viewId: number, args: ESObject, message: BinaryMessenger) {
    super();
    // 注册消息通道，通道名含 viewId 以支持多实例
    this.methodChannel = new MethodChannel(
      message, `com.example.ohos/customView${viewId}`, StandardMethodCodec.INSTANCE);
    this.methodChannel.setMethodCallHandler(this);
  }

  onMethodCall(call: MethodCall, result: MethodResult): void {
    switch (call.method) {
      case 'getMessageFromFlutterView':
        // 处理 Dart 侧消息
        result.success(true);
        break;
    }
  }

  public sendMessage = () => {
    // 向 Dart 侧发送消息
    this.methodChannel.invokeMethod('getMessageFromOhosView', 'native data');
  }

  getView(): WrappedBuilder<[Params]> {
    return new WrappedBuilder(ButtonBuilder);
  }

  dispose(): void { }
}
```

#### 3. 实现 PlatformViewFactory

```typescript
import PlatformViewFactory
  from '@ohos/flutter_ohos/src/main/ets/plugin/platform/PlatformViewFactory';

export class CustomFactory extends PlatformViewFactory {
  message: BinaryMessenger;

  constructor(message: BinaryMessenger, createArgsCodes: MessageCodec<Object>) {
    super(createArgsCodes);
    this.message = message;
  }

  public create(context: common.Context, viewId: number, args: Object): PlatformView {
    return new CustomView(context, viewId, args, this.message);
  }
}
```

#### 4. 实现 FlutterPlugin 注册 Factory

```typescript
import { FlutterPlugin, FlutterPluginBinding }
  from '@ohos/flutter_ohos/src/main/ets/embedding/engine/plugins/FlutterPlugin';

export class CustomPlugin implements FlutterPlugin {
  onAttachedToEngine(binding: FlutterPluginBinding): void {
    binding.getPlatformViewRegistry()?.registerViewFactory(
      'com.example.ohos/customView',  // viewType，须与 Dart 侧一致
      new CustomFactory(binding.getBinaryMessenger(), StandardMessageCodec.INSTANCE));
  }
  onDetachedFromEngine(binding: FlutterPluginBinding): void {}
}
```

#### 5. 在 EntryAbility 中注册 Plugin

```typescript
export default class EntryAbility extends FlutterAbility {
  configureFlutterEngine(flutterEngine: FlutterEngine) {
    super.configureFlutterEngine(flutterEngine)
    GeneratedPluginRegistrant.registerWith(flutterEngine)
    this.addPlugin(new CustomPlugin());
  }
}
```

### Dart 侧实现

#### 1. 使用 OhosView 嵌入

```dart
class CustomOhosView extends StatefulWidget {
  final OnViewCreated onViewCreated;
  const CustomOhosView(this.onViewCreated, {super.key});

  @override
  State<CustomOhosView> createState() => _CustomOhosViewState();
}

class _CustomOhosViewState extends State<CustomOhosView> {
  late MethodChannel _channel;

  @override
  Widget build(BuildContext context) {
    return OhosView(
      viewType: 'com.example.ohos/customView',  // 须与 Native 侧一致
      onPlatformViewCreated: _onPlatformViewCreated,
      creationParams: const <String, dynamic>{'initParams': 'hello world'},
      creationParamsCodec: const StandardMessageCodec(),
    );
  }

  void _onPlatformViewCreated(int id) {
    // 创建后绑定 MethodChannel（通道名含 viewId）
    _channel = MethodChannel('com.example.ohos/customView$id');
    final controller = CustomViewController._(_channel);
    widget.onViewCreated(controller);
  }
}
```

#### 2. 封装 Controller 实现双向通信

```dart
class CustomViewController {
  final MethodChannel _channel;
  final StreamController<String> _controller = StreamController<String>();

  CustomViewController._(this._channel) {
    _channel.setMethodCallHandler((call) async {
      switch (call.method) {
        case 'getMessageFromOhosView':
          final result = call.arguments as String;
          _controller.sink.add(result);
          break;
      }
    });
  }

  Stream<String> get customDataStream => _controller.stream;

  Future<void> sendMessageToOhosView(String message) async {
    await _channel.invokeMethod('getMessageFromFlutterView', message);
  }
}
```

---

## Channel 通信

Flutter OHos 支持三种 Platform Channel。

### MethodChannel（方法调用）

最常用，适合请求-响应模式。

**Dart 侧**：

```dart
final _platform = const MethodChannel('samples.flutter.dev/battery');
final result = await _platform.invokeMethod<int>('getBatteryLevel');
```

**ETS 侧**：

```typescript
onAttachedToEngine(binding: FlutterPluginBinding): void {
  this.channel = new MethodChannel(binding.getBinaryMessenger(), "samples.flutter.dev/battery");
  this.channel.setMethodCallHandler({
    onMethodCall(call: MethodCall, result: MethodResult) {
      switch (call.method) {
        case "getBatteryLevel":
          result.success(/* 返回值 */);
          break;
        default:
          result.notImplemented();
          break;
      }
    }
  });
}
```

### BasicMessageChannel（消息传递）

适合双向消息传递，使用编解码器序列化。

**Dart 侧**：

```dart
final _basicChannel = const BasicMessageChannel(
  "samples.flutter.dev/basic_channel", StandardMessageCodec());
String result = await _basicChannel.send(++count) as String;
```

**ETS 侧**：

```typescript
this.basicChannel = new BasicMessageChannel(
  binding.getBinaryMessenger(), "samples.flutter.dev/basic_channel", new StandardMessageCodec());
this.basicChannel.setMessageHandler({
  onMessage(message: Any, reply: Reply<Any>) {
    if (message % 2 == 0) {
      reply.reply("run with if case.");
    } else {
      reply.reply("run with else case");
    }
  }
});
```

### EventChannel（事件流）

适合持续事件流（传感器、状态变化等）。

**Dart 侧**：

```dart
final _eventChannel = const EventChannel('samples.flutter.dev/event_channel');
_eventChannel.receiveBroadcastStream().listen((event) {
  setState(() { message = "Event: $event"; });
});
```

**ETS 侧**：

```typescript
private eventSink?: EventSink;

this.eventChannel = new EventChannel(binding.getBinaryMessenger(), "samples.flutter.dev/event_channel");
this.eventChannel.setStreamHandler({
  onListen(args: Any, events: EventSink): void {
    this.eventSink = events;
  },
  onCancel(args: Any): void {
    this.eventSink = undefined;
  }
});

// 发送事件
this.eventSink?.success("event data");
```

### Plugin 注册模式

所有 Channel 通常在 FlutterPlugin 的 `onAttachedToEngine` 中注册：

```typescript
export class MyPlugin implements FlutterPlugin {
  onAttachedToEngine(binding: FlutterPluginBinding): void {
    new MethodChannel(binding.getBinaryMessenger(), "my.channel")
      .setMethodCallHandler(this);
  }
  onDetachedFromEngine(binding: FlutterPluginBinding): void {}
}

// EntryAbility.ets
this.addPlugin(new MyPlugin());
```

### 通道选择指南

| 场景 | 推荐 Channel | 说明 |
|------|-------------|------|
| 一次性方法调用 | MethodChannel | 请求-响应模式 |
| 双向消息传递 | BasicMessageChannel | 支持编解码 |
| 持续事件流 | EventChannel | 传感器、状态变化 |
| PlatformView 通信 | MethodChannel（含 viewId） | 通道名带 viewId 支持多实例 |
