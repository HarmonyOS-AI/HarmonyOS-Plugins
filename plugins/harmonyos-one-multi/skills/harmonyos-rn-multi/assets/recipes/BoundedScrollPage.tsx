import type { PropsWithChildren, ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

type Props = PropsWithChildren<{
  header?: ReactNode;
  footer?: ReactNode;
}>;

export function BoundedScrollPage({ header, children, footer }: Props) {
  return (
    <View style={styles.page}>
      {header}
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        style={styles.viewport}
      >
        {children}
      </ScrollView>
      {footer}
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    minHeight: 0,
  },
  viewport: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
  },
});
