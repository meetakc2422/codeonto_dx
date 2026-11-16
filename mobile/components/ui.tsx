import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Theme } from '../constants/Colors';

export const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
export const rupees = (v: number | null | undefined) => (v == null ? '—' : `${v < 0 ? '-' : ''}₹${inr.format(Math.abs(Math.round(v)))}`);
export function rupeesShort(v: number | null | undefined) {
  if (v == null) return '—';
  const a = Math.abs(v), s = v < 0 ? '-' : '';
  if (a >= 1e7) return `${s}₹${(a / 1e7).toFixed(2)} Cr`;
  if (a >= 1e5) return `${s}₹${(a / 1e5).toFixed(2)} L`;
  if (a >= 1e3) return `${s}₹${(a / 1e3).toFixed(1)}k`;
  return `${s}₹${Math.round(a)}`;
}
export const minutesText = (m: number | null | undefined) => {
  if (m == null) return '—';
  const h = Math.floor(m / 60), r = Math.round(m % 60);
  return h ? `${h}h ${r}m` : `${r}m`;
};
export function ago(ts?: string | null) {
  if (!ts) return '';
  const s = (Date.now() - new Date(ts).getTime()) / 1000;
  if (s < 90) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}
export const shortDate = (d?: string | null) =>
  d ? new Date(d.length === 10 ? `${d}T00:00:00` : d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '';

/** A white card on the black page. `tint` makes it a pastel one (the insight cards). */
export function Card({ children, style, tint }: { children: React.ReactNode; style?: ViewStyle; tint?: string }) {
  return <View style={[s.card, tint ? { backgroundColor: tint } : null, style]}>{children}</View>;
}

export function CardTitle({ label, title, right }: { label?: string; title: string; right?: React.ReactNode }) {
  return (
    <View style={s.cardHead}>
      <View style={{ flex: 1 }}>
        {label ? <Text style={s.cardLabel}>{label}</Text> : null}
        <Text style={s.cardTitle}>{title}</Text>
      </View>
      {right}
    </View>
  );
}

/** The big number at the top of a screen, on a pastel card. */
export function Hero({ big, label, sub, tone = 'normal' }: { big: string; label: string; sub?: string; tone?: 'normal' | 'bad' }) {
  return (
    <View style={[s.card, { backgroundColor: tone === 'bad' ? Theme.rose : Theme.mint, borderRadius: 26, padding: 20 }]}>
      <Text style={s.heroBig}>{big}</Text>
      <Text style={s.heroLabel}>{label}</Text>
      {sub ? <Text style={s.heroSub}>{sub}</Text> : null}
    </View>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: 'bad' | 'warn' | 'ok' }) {
  const color = tone === 'bad' ? Theme.bad : tone === 'warn' ? Theme.warn : tone === 'ok' ? Theme.good : Theme.ink;
  return (
    <View style={s.stat}>
      <Text style={s.statLabel}>{label}</Text>
      <Text style={[s.statValue, { color }]}>{value}</Text>
      {sub ? <Text style={s.statSub}>{sub}</Text> : null}
    </View>
  );
}

export const Row = ({ children }: { children: React.ReactNode }) => <View style={s.row}>{children}</View>;

type Tone = 'grey' | 'red' | 'amber' | 'green' | 'blue';
/** A small label. On a white card it is pastel; `dark` is for use on the black page, where the active one is blue. */
export function Pill({ text, tone = 'grey', onPress, active, dark }: { text: string; tone?: Tone; onPress?: () => void; active?: boolean; dark?: boolean }) {
  const light = { grey: ['#F1F2F4', Theme.inkMuted], red: [Theme.badSoft, Theme.bad], amber: [Theme.warnSoft, Theme.warn], green: [Theme.goodSoft, Theme.good], blue: ['#DCEBFF', '#2563EB'] } as const;
  const [bg, fg] = dark ? (active ? [Theme.accent, Theme.white] : [Theme.chip, Theme.whiteMuted]) : light[tone];
  const body = (
    <View style={[s.pill, { backgroundColor: bg }]}>
      <Text style={[s.pillText, { color: fg }]}>{text}</Text>
    </View>
  );
  return onPress ? <Pressable onPress={onPress}>{body}</Pressable> : body;
}

export function SectionTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <View style={{ marginTop: 20, marginBottom: 10 }}>
      <Text style={s.sectionTitle}>{title}</Text>
      {hint ? <Text style={s.hint}>{hint}</Text> : null}
    </View>
  );
}

export const Loading = () => <ActivityIndicator color={Theme.accent} style={{ marginTop: 40 }} />;
export const Empty = ({ text }: { text: string }) => <Text style={s.empty}>{text}</Text>;
export const ErrorBox = ({ text, onRetry }: { text: string; onRetry?: () => void }) => (
  <Card>
    <Text style={{ color: Theme.bad, fontWeight: '700' }}>Couldn't load this</Text>
    <Text style={s.cardHint}>{text}</Text>
    {onRetry ? <Pressable onPress={onRetry}><Text style={{ color: Theme.ink, marginTop: 8, fontWeight: '700' }}>Try again</Text></Pressable> : null}
  </Card>
);

export const ink = { color: Theme.ink } as const;
export const muted = { color: Theme.inkMuted } as const;

const s = StyleSheet.create({
  card: { backgroundColor: Theme.paper, borderRadius: 24, padding: 16, marginBottom: 12 },
  cardHead: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 10 },
  cardLabel: { color: Theme.inkMuted, fontSize: 12 },
  cardTitle: { color: Theme.ink, fontSize: 18, fontWeight: '800', marginTop: 2 },
  cardHint: { color: Theme.inkMuted, fontSize: 12, marginTop: 3, lineHeight: 17 },
  heroBig: { color: Theme.ink, fontSize: 44, fontWeight: '800' },
  heroLabel: { color: Theme.ink, fontSize: 15, fontWeight: '600', marginTop: 2 },
  heroSub: { color: Theme.inkMuted, fontSize: 12, marginTop: 8, lineHeight: 17 },
  stat: { flex: 1, backgroundColor: Theme.paper, borderRadius: 20, padding: 14 },
  statLabel: { color: Theme.inkMuted, fontSize: 11 },
  statValue: { fontSize: 22, fontWeight: '800', marginTop: 4 },
  statSub: { color: Theme.inkMuted, fontSize: 11, marginTop: 2 },
  row: { flexDirection: 'row', gap: 10, marginBottom: 10 },
  pill: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999, marginRight: 6, marginBottom: 6 },
  pillText: { fontSize: 12, fontWeight: '700' },
  sectionTitle: { color: Theme.white, fontSize: 18, fontWeight: '800' },
  hint: { color: Theme.whiteMuted, fontSize: 12, marginTop: 2 },
  empty: { color: Theme.whiteMuted, textAlign: 'center', marginTop: 30 },
});
