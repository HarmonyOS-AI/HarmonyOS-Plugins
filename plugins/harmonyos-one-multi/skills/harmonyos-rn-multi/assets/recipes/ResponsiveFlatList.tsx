import { useMemo } from 'react';
import type { ListRenderItem } from 'react-native';
import { FlatList, StyleSheet, View } from 'react-native';

type KeyedItem = Readonly<{ id: string }>;

type Props<T extends KeyedItem> = Readonly<{
  items: readonly T[];
  columns: number;
  renderItem: ListRenderItem<T>;
  // Keep filters, selection, route state and business anchors outside this component.
  extraData?: unknown;
}>;

export function ResponsiveFlatList<T extends KeyedItem>({
  items,
  columns,
  renderItem,
  extraData,
}: Props<T>) {
  const listExtraData = useMemo(
    () => ({ columns, extraData }),
    [columns, extraData],
  );

  return (
    <FlatList
      key={`presentation-columns-${columns}`}
      contentContainerStyle={styles.content}
      data={items}
      extraData={listExtraData}
      keyExtractor={(item) => item.id}
      numColumns={columns}
      renderItem={(info) => (
        <View style={styles.cell}>{renderItem(info)}</View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  content: {
    flexGrow: 1,
  },
  cell: {
    flex: 1,
    minWidth: 0,
  },
});
