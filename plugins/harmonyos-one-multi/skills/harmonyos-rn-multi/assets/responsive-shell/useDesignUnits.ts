import { useCallback, useMemo } from 'react';
import { useWindowDimensions } from 'react-native';

export type DesignUnitConfig = Readonly<{
  designWidth: number;
  maxContentWidth: number;
  minScale: number;
  maxScale: number;
}>;

const DEFAULT_CONFIG: DesignUnitConfig = {
  // Replace these sample values with the project's design system.
  designWidth: 375,
  maxContentWidth: 960,
  minScale: 0.9,
  maxScale: 1.2,
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function resolveLayoutScale(
  width: number,
  config: DesignUnitConfig = DEFAULT_CONFIG,
): number {
  const contentWidth = Math.min(width, config.maxContentWidth);
  return clamp(
    contentWidth / config.designWidth,
    config.minScale,
    config.maxScale,
  );
}

export function useDesignUnits(config: DesignUnitConfig = DEFAULT_CONFIG) {
  const { width, height, fontScale, scale } = useWindowDimensions();
  const layoutScale = useMemo(
    () => resolveLayoutScale(width, config),
    [config, width],
  );
  const unit = useCallback(
    (designValue: number) => designValue * layoutScale,
    [layoutScale],
  );

  return {
    width,
    height,
    fontScale,
    pixelRatio: scale,
    layoutScale,
    unit,
  } as const;
}
