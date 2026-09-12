import type { PropsWithChildren } from 'react';
import { useEffect, useRef, useState } from 'react';
import type { LayoutChangeEvent, ScaledSize } from 'react-native';
import { Dimensions, View, useWindowDimensions } from 'react-native';

export type WindowEvidence = Readonly<{
  name: string;
  sequence: number;
  timestamp: number;
  window: ScaledSize;
  wrapper: Readonly<{ x: number; y: number; width: number; height: number }>;
}>;

type Props = PropsWithChildren<{
  name: string;
  onEvidence: (evidence: WindowEvidence) => void;
}>;

export function WindowEvidenceProbe({ name, onEvidence, children }: Props) {
  const window = useWindowDimensions();
  const sequence = useRef(0);
  const [wrapper, setWrapper] = useState({ x: 0, y: 0, width: 0, height: 0 });

  useEffect(() => {
    sequence.current += 1;
    onEvidence({
      name,
      sequence: sequence.current,
      timestamp: Date.now(),
      window: Dimensions.get('window'),
      wrapper,
    });
  }, [name, onEvidence, window.fontScale, window.height, window.scale, window.width, wrapper]);

  const handleLayout = (event: LayoutChangeEvent) => {
    setWrapper(event.nativeEvent.layout);
  };

  return <View onLayout={handleLayout}>{children}</View>;
}
