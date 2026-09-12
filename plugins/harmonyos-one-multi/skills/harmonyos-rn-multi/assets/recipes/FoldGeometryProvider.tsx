import type { PropsWithChildren } from 'react';
import { createContext, useContext, useEffect, useState } from 'react';

export type FoldPosture = 'unknown' | 'folded' | 'expanded' | 'half-folded';

export type LayoutRect = Readonly<{
  x: number;
  y: number;
  width: number;
  height: number;
}>;

export type RawFoldSnapshot = Readonly<{
  supported: boolean;
  posture: unknown;
  creaseRects: readonly LayoutRect[];
  sequence: number;
}>;

export type FoldSnapshot = Readonly<{
  supported: boolean;
  posture: FoldPosture;
  creaseRects: readonly LayoutRect[];
  sequence: number;
  unit: 'rn-layout-unit';
}>;

export type FoldPort = Readonly<{
  getSnapshot: () => RawFoldSnapshot;
  subscribe: (listener: (snapshot: RawFoldSnapshot) => void) => () => void;
  normalizePosture: (value: unknown) => FoldPosture;
  toApplicationLayoutRect: (rect: LayoutRect) => LayoutRect;
}>;

const EMPTY: FoldSnapshot = {
  supported: false,
  posture: 'unknown',
  creaseRects: [],
  sequence: 0,
  unit: 'rn-layout-unit',
};

const FoldContext = createContext<FoldSnapshot>(EMPTY);

type Props = PropsWithChildren<{ port?: FoldPort }>;

export function FoldGeometryProvider({ port, children }: Props) {
  const [snapshot, setSnapshot] = useState<FoldSnapshot>(EMPTY);

  useEffect(() => {
    if (!port) {
      setSnapshot(EMPTY);
      return undefined;
    }

    let active = true;
    let lastSequence = -1;
    const publish = (raw: RawFoldSnapshot) => {
      if (!active || raw.sequence <= lastSequence) return;
      lastSequence = raw.sequence;
      setSnapshot({
        supported: raw.supported,
        posture: port.normalizePosture(raw.posture),
        creaseRects: raw.creaseRects.map((rect) => port.toApplicationLayoutRect(rect)),
        sequence: raw.sequence,
        unit: 'rn-layout-unit',
      });
    };

    // Subscribe first, then read a snapshot so changes between the two are resolved by sequence.
    const unsubscribe = port.subscribe(publish);
    publish(port.getSnapshot());

    return () => {
      active = false;
      unsubscribe();
    };
  }, [port]);

  return <FoldContext.Provider value={snapshot}>{children}</FoldContext.Provider>;
}

export function useFoldGeometry(): FoldSnapshot {
  return useContext(FoldContext);
}
