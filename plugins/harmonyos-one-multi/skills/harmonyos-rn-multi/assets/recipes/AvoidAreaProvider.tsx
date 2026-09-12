import type { PropsWithChildren } from 'react';
import { createContext, useContext, useEffect, useState } from 'react';

export type Insets = Readonly<{
  top: number;
  right: number;
  bottom: number;
  left: number;
}>;

export type RawAvoidSnapshot = Readonly<{
  insets: Insets;
  sequence: number;
}>;

export type AvoidSnapshot = Readonly<{
  insets: Insets;
  sequence: number;
  source: 'harmony-avoid' | 'fallback';
  unit: 'rn-layout-unit';
}>;

export type AvoidAreaPort = Readonly<{
  getSnapshot: () => RawAvoidSnapshot;
  subscribe: (listener: (snapshot: RawAvoidSnapshot) => void) => () => void;
  toApplicationLayoutInsets: (insets: Insets) => Insets;
}>;

const ZERO_INSETS: Insets = { top: 0, right: 0, bottom: 0, left: 0 };
const EMPTY: AvoidSnapshot = {
  insets: ZERO_INSETS,
  sequence: 0,
  source: 'fallback',
  unit: 'rn-layout-unit',
};

const AvoidAreaContext = createContext<AvoidSnapshot>(EMPTY);

type Props = PropsWithChildren<{ port?: AvoidAreaPort }>;

export function AvoidAreaProvider({ port, children }: Props) {
  const [snapshot, setSnapshot] = useState<AvoidSnapshot>(EMPTY);

  useEffect(() => {
    if (!port) {
      setSnapshot(EMPTY);
      return undefined;
    }

    let active = true;
    let lastSequence = -1;
    const publish = (raw: RawAvoidSnapshot) => {
      if (!active || raw.sequence <= lastSequence) return;
      lastSequence = raw.sequence;
      setSnapshot({
        insets: port.toApplicationLayoutInsets(raw.insets),
        sequence: raw.sequence,
        source: 'harmony-avoid',
        unit: 'rn-layout-unit',
      });
    };

    const unsubscribe = port.subscribe(publish);
    publish(port.getSnapshot());
    return () => {
      active = false;
      unsubscribe();
    };
  }, [port]);

  return (
    <AvoidAreaContext.Provider value={snapshot}>
      {children}
    </AvoidAreaContext.Provider>
  );
}

export function useAvoidArea(): AvoidSnapshot {
  return useContext(AvoidAreaContext);
}
