#!/usr/bin/env node

import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const scanner = new URL('./scan-rn-adaptation.mjs', import.meta.url);
const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'rnoh-scan-rules-'));
const safeFixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'rnoh-scan-safe-'));

const cases = {
  'image.tsx': `
    import { Image } from 'react-native';
    export const BadImage = () => (
      <Image source={{ uri: 'x' }} style={{ width: '100%', aspectRatio: 1.5 }} />
    );
  `,
  'flat-list.tsx': `
    import { FlatList } from 'react-native';
    export const BadList = ({ columns, data }) => (
      <FlatList data={data} numColumns={columns} renderItem={() => null} />
    );
  `,
  'list-geometry.tsx': `
    import { Dimensions, FlatList } from 'react-native';
    const itemWidth = Dimensions.get('window').width / 2;
    const getItemLayout = (_, index) => ({ length: itemWidth, offset: itemWidth * index, index });
    export const BadGeometry = ({ data }) => <FlatList data={data} getItemLayout={getItemLayout} />;
  `,
  'scroll.tsx': `
    import { ScrollView } from 'react-native';
    export const BadScroll = () => <ScrollView style={{ height: 800 }} />;
  `,
  'avoid.tsx': `
    import { KeyboardAvoidingView } from 'react-native';
    import { Avoid, AvoidAreaType } from '@hadss/react_native_avoid_area';
    Avoid.addAvoidAreaListener(() => {});
    const area = Avoid.getWindowAvoidArea(AvoidAreaType.TYPE_KEYBOARD);
    export const BadAvoid = () => <KeyboardAvoidingView>{area.bottomRect.height}</KeyboardAvoidingView>;
  `,
  'fold.tsx': `
    import { Fold } from '@hadss/react_native_adaptive_layout';
    let foldStatus = 0;
    Fold.addFoldListener((next) => { foldStatus = next; });
    export const halfFolded = foldStatus === 3;
  `,
  'orientation.tsx': `
    import Orientation from 'react-native-orientation';
    Orientation.addOrientationListener(() => {});
    Orientation.lockToLandscape();
  `,
};

try {
  for (const [name, source] of Object.entries(cases)) {
    fs.writeFileSync(path.join(fixtureRoot, name), source);
  }

  const result = spawnSync(process.execPath, [scanner.pathname, fixtureRoot], {
    encoding: 'utf8',
  });
  const output = `${result.stdout}\n${result.stderr}`;
  const expectedRuleIds = [
    'image-percent-aspect-ratio',
    'flatlist-dynamic-columns-without-key',
    'list-window-geometry-audit',
    'scrollview-fixed-viewport-height',
    'avoid-listener-without-remove',
    'avoid-area-without-unit-boundary',
    'duplicate-keyboard-avoidance-owner',
    'fold-listener-without-initial-snapshot',
    'fold-listener-without-remove',
    'fold-status-numeric-comparison',
    'orientation-listener-without-remove',
    'orientation-lock-without-restore',
  ];

  for (const ruleId of expectedRuleIds) {
    assert.match(output, new RegExp(`\\b${ruleId}\\b`), `missing ${ruleId}\n${output}`);
  }

  fs.writeFileSync(path.join(safeFixtureRoot, 'safe.tsx'), `
    import { FlatList, Image, ScrollView, View, useWindowDimensions } from 'react-native';
    import Orientation from 'react-native-orientation';
    import { Fold } from '@hadss/react_native_adaptive_layout';
    import { Avoid, AvoidAreaType } from '@hadss/react_native_avoid_area';

    const onFold = () => {};
    const onOrientation = () => {};
    const toLayoutUnit = (area) => area;
    const foldStatus = Fold.getFoldStatus();
    Fold.addFoldListener(onFold);
    Fold.removeFoldListener(onFold);
    Orientation.addOrientationListener(onOrientation);
    Orientation.removeOrientationListener(onOrientation);
    Orientation.lockToLandscape();
    Orientation.unlockAllOrientations();
    Avoid.addAvoidAreaListener(() => {});
    Avoid.removeAvoidAreaListener();
    const area = toLayoutUnit(Avoid.getWindowAvoidArea(AvoidAreaType.TYPE_SYSTEM));

    export const Safe = ({ columns, data, source }) => {
      const { width } = useWindowDimensions();
      const itemWidth = width / columns;
      return (
        <View style={{ width: '100%', aspectRatio: 1.5 }}>
          <Image source={source} style={{ width: '100%', height: '100%' }} />
          <FlatList
            key={\`columns-\${columns}\`}
            data={data}
            numColumns={columns}
            extraData={{ columns, itemWidth }}
          />
          <ScrollView style={{ flex: 1 }} />
          {foldStatus === 'half-folded' ? area.top : null}
        </View>
      );
    };
  `);

  const safeResult = spawnSync(process.execPath, [scanner.pathname, safeFixtureRoot], {
    encoding: 'utf8',
  });
  const safeOutput = `${safeResult.stdout}\n${safeResult.stderr}`;
  for (const ruleId of expectedRuleIds) {
    assert.doesNotMatch(
      safeOutput,
      new RegExp(`\\b${ruleId}\\b`),
      `false positive ${ruleId}\n${safeOutput}`,
    );
  }

  console.log(`PASS: ${expectedRuleIds.length} positive and negative scanner checks.`);
} finally {
  fs.rmSync(fixtureRoot, { recursive: true, force: true });
  fs.rmSync(safeFixtureRoot, { recursive: true, force: true });
}
