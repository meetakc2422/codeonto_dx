import React from 'react';
import Svg, { Circle, G, Path, Rect, Text as SvgText } from 'react-native-svg';
import { Theme } from '../constants/Colors';

/** A smooth line through the values, scaled to fit. */
export function Sparkline({ values, color, width = 300, height = 70 }: { values: number[]; color: string; width?: number; height?: number }) {
  if (values.length < 2) return <Svg width={width} height={height} />;
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
  const pad = 6;
  const pts = values.map((v, i) => [pad + (i * (width - 2 * pad)) / (values.length - 1), height - pad - ((v - min) / span) * (height - 2 * pad)]);
  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], cx = (x0 + x1) / 2;
    d += ` C ${cx} ${y0}, ${cx} ${y1}, ${x1} ${y1}`;
  }
  return (
    <Svg width={width} height={height}>
      <Path d={d} stroke={color} strokeWidth={2.5} fill="none" strokeLinecap="round" />
    </Svg>
  );
}

/** A ring split into coloured parts with a number in the middle. */
export function Donut({ parts, center, size = 130 }: { parts: { value: number; color: string }[]; center: string; size?: number }) {
  const total = parts.reduce((t, p) => t + p.value, 0);
  const r = size / 2 - 14, c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <Svg width={size} height={size}>
      <G rotation={-90} origin={`${size / 2}, ${size / 2}`}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke="#EEF0F2" strokeWidth={22} fill="none" />
        {total > 0 ? parts.filter((p) => p.value > 0).map((p, i) => {
          const len = (p.value / total) * c;
          const el = <Circle key={i} cx={size / 2} cy={size / 2} r={r} stroke={p.color} strokeWidth={22} fill="none" strokeDasharray={`${len} ${c - len}`} strokeDashoffset={-offset} />;
          offset += len;
          return el;
        }) : null}
      </G>
      <SvgText x={size / 2} y={size / 2 + 6} fontSize={18} fontWeight="700" fill={Theme.ink} textAnchor="middle">{center}</SvgText>
    </Svg>
  );
}

/** Vertical bars with a label and value under each. */
export function Bars({ items, height = 120 }: { items: { label: string; value: number; color: string }[]; height?: number }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  const w = 56, gap = 22, width = items.length * (w + gap);
  return (
    <Svg width={width} height={height + 34}>
      {items.map((it, i) => {
        const h = Math.max(4, (it.value / max) * height);
        const x = i * (w + gap) + gap / 2;
        return (
          <G key={it.label}>
            <Rect x={x} y={height - h + 16} width={w} height={h} rx={8} fill={it.color} />
            <SvgText x={x + w / 2} y={height - h + 11} fontSize={12} fontWeight="700" fill={Theme.ink} textAnchor="middle">{it.value.toFixed(1)}</SvgText>
            <SvgText x={x + w / 2} y={height + 30} fontSize={11} fill={Theme.inkMuted} textAnchor="middle">{it.label}</SvgText>
          </G>
        );
      })}
    </Svg>
  );
}
