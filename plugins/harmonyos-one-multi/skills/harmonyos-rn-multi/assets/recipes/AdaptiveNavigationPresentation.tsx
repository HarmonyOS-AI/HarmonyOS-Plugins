import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useAppBreakpoint } from './BreakpointProvider';

type Props = Readonly<{
  navigation: ReactNode;
  detail: ReactNode;
  hasSelection: boolean;
  onCompactBack: () => void;
}>;

export function AdaptiveNavigationPresentation({
  navigation,
  detail,
  hasSelection,
  onCompactBack,
}: Props) {
  const { value: breakpoint } = useAppBreakpoint();
  const expanded = breakpoint === 'expanded';

  if (!expanded) {
    return hasSelection ? (
      <View style={styles.pane}>
        <Pressable onPress={onCompactBack} style={styles.backButton}>
          <Text>返回列表</Text>
        </Pressable>
        {detail}
      </View>
    ) : (
      <View style={styles.pane}>{navigation}</View>
    );
  }

  return (
    <View style={styles.row}>
      <View style={styles.navigation}>{navigation}</View>
      <View style={styles.detail}>{detail}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  pane: { flex: 1, minWidth: 0 },
  row: { flex: 1, flexDirection: 'row' },
  navigation: { flexBasis: 360, flexGrow: 0, flexShrink: 1, minWidth: 0 },
  detail: { flex: 1, minWidth: 0 },
  backButton: { alignSelf: 'flex-start', padding: 12 },
});
