import type { ImageSourcePropType, ImageStyle, StyleProp, ViewStyle } from 'react-native';
import { Image, StyleSheet, View } from 'react-native';

type Props = Readonly<{
  source: ImageSourcePropType;
  aspectRatio: number;
  resizeMode?: 'cover' | 'contain';
  containerStyle?: StyleProp<ViewStyle>;
  imageStyle?: StyleProp<ImageStyle>;
  accessibilityLabel?: string;
}>;

export function ResponsiveImage({
  source,
  aspectRatio,
  resizeMode = 'cover',
  containerStyle,
  imageStyle,
  accessibilityLabel,
}: Props) {
  return (
    <View style={[styles.container, { aspectRatio }, containerStyle]}>
      <Image
        accessibilityLabel={accessibilityLabel}
        resizeMode={resizeMode}
        source={source}
        style={[styles.image, imageStyle]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: '100%',
  },
});
