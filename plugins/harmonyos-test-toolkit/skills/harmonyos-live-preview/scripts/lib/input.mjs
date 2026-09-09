// Translates browser input events (sent by the viewer) into HarmonyOS Previewer engine commands.
// This is the same control channel DevEco's preview-server uses: the engine accepts JSON commands
// `{version, command, type, args}` framed with a trailing NUL over the Unix command pipe, and the
// bridge writes them via engine.send(). This module is pure assembly — no I/O — so the command
// vocabulary lives in one place.
//
// Verified end-to-end against the SDK Previewer (4.3.3): MousePress/MouseMove/MouseRelease drive
// the pointer (a tap = press+release, a swipe/scroll = press + moves + release), BackClicked pops
// the route, and KeyPress feeds the focused input (text confirmed rendering into a TextInput).
//
// keyCode values are the SDK's (oh_key_code.h). keyAction uses the *Previewer's own* enum —
// DOWN=0, UP=1, PRESS=2 — which is NOT @ohos.multimodalInput.keyEvent.Action (DOWN=1/UP=2). A
// keystroke fires the DOM order down → press → up; with the wrong enum the engine still acks
// result:true but inserts nothing, so this distinction matters.

const VERSION = '1.0.1';
const KEY_ACTION = { down: 0, up: 1, press: 2 };

const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);

// JS KeyboardEvent (key/code) → HarmonyOS KeyCode (oh_key_code.h). Common typing subset; the
// engine ignores keyCode -1, so unmapped keys are simply dropped.
function keyCodeFor(key = '', code = '') {
  if (code.startsWith('Key') && code.length === 4) return 2017 + (code.charCodeAt(3) - 65); // A..Z → 2017..2042
  if (code.startsWith('Digit') && code.length === 6) return 2000 + (code.charCodeAt(5) - 48); // 0..9 → 2000..2009
  if (key && key.length === 1) {
    const c = key.toLowerCase();
    if (c >= 'a' && c <= 'z') return 2017 + (c.charCodeAt(0) - 97);
    if (c >= '0' && c <= '9') return 2000 + (c.charCodeAt(0) - 48);
    if (c === ' ') return 2050;
  }
  switch (key || code) {
    case ' ':
    case 'Space': return 2050;
    case 'Backspace': return 2055;
    case 'Enter': return 2054;
    case 'Tab': return 2049;
    default: return -1;
  }
}

function pointerCommand(phase, x, y) {
  const command = phase === 'down' ? 'MousePress' : phase === 'up' ? 'MouseRelease' : 'MouseMove';
  return { version: VERSION, command, type: 'action', args: { x, y, button: 0, duration: 0 } };
}

function keyPressCommands(keyCode, keyString) {
  // Mirror DevEco's web previewer: fire down → press → up. The focused control inserts on this
  // sequence; keyString carries the character to insert.
  return [KEY_ACTION.down, KEY_ACTION.press, KEY_ACTION.up].map((keyAction) => ({
    version: VERSION,
    command: 'KeyPress',
    type: 'action',
    args: { isInputMethod: false, keyCode, keyAction, keyString, pressedCodes: [keyCode] },
  }));
}

// In-place resolution change — the engine's own `ResolutionSwitch`, which DevEco drives when you
// drag a preview window's edge. Unlike the pointer/key commands this one is a *set* command
// (ide_previewer cli/CommandLine.cpp implements RunSet only), so an `action` envelope would be
// silently dropped. originWidth/Height is the device's real resolution and width/height the rendered
// one; this skill always keeps them equal (the frame IS the device pixels, no extra compression).
// `reason` is what lets ArkUI tell a rotation apart from a dragged resize.
function resizeCommand({ width, height, density, reason }) {
  return {
    version: VERSION,
    command: 'ResolutionSwitch',
    type: 'set',
    args: {
      originWidth: width,
      originHeight: height,
      width,
      height,
      screenDensity: density,
      reason: reason === 'rotation' || reason === 'undefined' ? reason : 'resize',
    },
  };
}

// Map one viewer message to zero or more engine commands.
//   { t:'p', phase:'down'|'move'|'up', x, y }  — x/y are normalized 0..1 over the rendered frame
//   { t:'key', key, code, keyString? }          — a keystroke for the focused input
//   { t:'back' }                                — system back
//   { t:'resize', width, height, density, reason? } — change this engine's size in place
//   { t:'raw', command, args?, type? }          — escape hatch: send any pipe command verbatim
//                                                 (the engine's vocabulary is wider than the viewer
//                                                 needs — Resolution, LoadDocument, FoldStatus, … —
//                                                 and this lets tooling drive it without a new route)
export function eventToCommands(msg, resolution) {
  const [rw, rh] = resolution;
  switch (msg?.t) {
    case 'p': {
      if (!['down', 'move', 'up'].includes(msg.phase)) return [];
      const x = clamp(Math.round(msg.x * rw), 0, rw - 1);
      const y = clamp(Math.round(msg.y * rh), 0, rh - 1);
      return [pointerCommand(msg.phase, x, y)];
    }
    case 'key': {
      const keyCode = keyCodeFor(msg.key, msg.code);
      if (keyCode < 0) return [];
      const keyString = typeof msg.keyString === 'string' ? msg.keyString
        : (msg.key && msg.key.length === 1 ? msg.key : '');
      return keyPressCommands(keyCode, keyString);
    }
    case 'back':
      return [{ version: VERSION, command: 'BackClicked', type: 'action', args: {} }];
    case 'resize':
      return [resizeCommand(msg)];
    case 'raw': {
      if (typeof msg.command !== 'string' || !msg.command) return [];
      const args = msg.args && typeof msg.args === 'object' ? msg.args : {};
      // Most of the vocabulary is `action`, but a few commands (ResolutionSwitch, FoldStatus, …)
      // only implement RunSet and are dropped unless the envelope says `set` — hence the override.
      const type = msg.type === 'set' || msg.type === 'get' ? msg.type : 'action';
      return [{ version: VERSION, command: msg.command, type, args }];
    }
    default:
      return [];
  }
}
