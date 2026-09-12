import { useMemo } from 'react';
import { useWindowDimensions } from 'react-native';

export type Breakpoint = 'compact' | 'medium' | 'expanded';

// Replace these sample values with the project's design tokens or measured content breakpoints.
export const BREAKPOINTS = {
  medium: 600,
  expanded: 840,
} as const;

export function resolveBreakpoint(width: number): Breakpoint {
  if (width >= BREAKPOINTS.expanded) return 'expanded';
  if (width >= BREAKPOINTS.medium) return 'medium';
  return 'compact';
}

export function useBreakpoint(): Breakpoint {
  const { width } = useWindowDimensions();
  return useMemo(() => resolveBreakpoint(width), [width]);
}
