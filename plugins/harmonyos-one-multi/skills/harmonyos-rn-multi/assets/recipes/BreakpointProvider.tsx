import type { PropsWithChildren } from 'react';
import { createContext, useContext, useMemo } from 'react';
import { useWindowDimensions } from 'react-native';

export type AppBreakpoint = 'compact' | 'medium' | 'expanded';

export type BreakpointThresholds = Readonly<{
  medium: number;
  expanded: number;
}>;

export type BreakpointSnapshot = Readonly<{
  value: AppBreakpoint;
  width: number;
  height: number;
}>;

const BreakpointContext = createContext<BreakpointSnapshot | null>(null);

function resolveBreakpoint(
  width: number,
  thresholds: BreakpointThresholds,
): AppBreakpoint {
  if (width >= thresholds.expanded) return 'expanded';
  if (width >= thresholds.medium) return 'medium';
  return 'compact';
}

type Props = PropsWithChildren<{
  // Pass project tokens or measured content breakpoints. These are not platform constants.
  thresholds: BreakpointThresholds;
}>;

export function BreakpointProvider({ thresholds, children }: Props) {
  const { width, height } = useWindowDimensions();
  const { medium, expanded } = thresholds;
  const value = useMemo<BreakpointSnapshot>(
    () => ({
      value: resolveBreakpoint(width, { medium, expanded }),
      width,
      height,
    }),
    [expanded, height, medium, width],
  );

  return (
    <BreakpointContext.Provider value={value}>
      {children}
    </BreakpointContext.Provider>
  );
}

export function useAppBreakpoint(): BreakpointSnapshot {
  const value = useContext(BreakpointContext);
  if (!value) {
    throw new Error('useAppBreakpoint must be used inside BreakpointProvider');
  }
  return value;
}
