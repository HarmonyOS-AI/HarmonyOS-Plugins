import type { PropsWithChildren } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

type Props = PropsWithChildren<{
  backgroundColor: string;
  consumeTop?: boolean;
  consumeBottom?: boolean;
}>;

// Requires one SafeAreaProvider above the navigation/portal root.
export function SafeAreaOwnedPage({
  backgroundColor,
  consumeTop = true,
  consumeBottom = true,
  children,
}: Props) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.root, { backgroundColor }]}>
      <View
        style={[
          styles.content,
          consumeTop && { paddingTop: insets.top },
          consumeBottom && { paddingBottom: insets.bottom },
        ]}
      >
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  content: { flex: 1 },
});
