import type { PropsWithChildren } from 'react';
import { KeyboardAvoidingView, ScrollView, StyleSheet } from 'react-native';

type Props = PropsWithChildren<{
  // Choose from the locked RNOH/Host behavior; do not hard-code one policy for every page.
  behavior?: 'height' | 'padding' | 'position';
  keyboardVerticalOffset?: number;
}>;

export function KeyboardAwareForm({
  behavior,
  keyboardVerticalOffset = 0,
  children,
}: Props) {
  return (
    <KeyboardAvoidingView
      behavior={behavior}
      keyboardVerticalOffset={keyboardVerticalOffset}
      style={styles.page}
    >
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        style={styles.viewport}
      >
        {children}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, minHeight: 0 },
  viewport: { flex: 1 },
  content: { flexGrow: 1 },
});
