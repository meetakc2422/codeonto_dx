import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Colors } from '../constants/Colors';

const C = Colors.dark;

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

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[s.card, style]}>{children}</View>;
}

export function Hero({ big, label, sub, tone = 'normal' }: { big: string; label: string; sub?: string; tone?: 'normal' | 'bad' }) {
  return (
    <View style={[s.hero, tone === 'bad' && { borderColor: 'rgba(239,68,68,0.5)' }]}>
      <Text style={s.heroBig}>{big}</Text>
      <Text style={s.heroLabel}>{label}</Text>
      {sub ? <Text style={s.heroSub}>{sub}</Text> : null}
    </View>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: 'bad' | 'warn' | 'ok' }) {
  const color = tone === 'bad' ? Colors.danger : tone === 'warn' ? Colors.warning : tone === 'ok' ? Colors.success : C.text;
  return (
    <View style={s.stat}>
      <Text style={s.statLabel}>{label}</Text>
      <Text style={[s.statValue, { color }]}>{value}</Text>
      {sub ? <Text style={s.statSub}>{sub}</Text> : null}
    </View>
  );
}

export const Row = ({ children }: { children: React.ReactNode }) => <View style={s.row}>{children}</View>;

export function Pill({ text, tone = 'grey', onPress, active }: { text: string; tone?: 'grey' | 'red' | 'amber' | 'green' | 'blue'; onPress?: () => void; active?: boolean }) {
  const map = { grey: ['#1f2937', C.textSecondary], red: ['rgba(239,68,68,0.15)', '#F87171'], amber: ['rgba(245,158,11,0.15)', '#FBBF24'], green: ['rgba(16,185,129,0.15)', '#34D399'], blue: ['rgba(59,130,246,0.15)', '#60A5FA'] } as const;
  const [bg, fg] = map[tone];
  const body = (
    <View style={[s.pill, { backgroundColor: active ? Colors.primary : bg }]}>
      <Text style={[s.pillText, { color: active ? '#fff' : fg }]}>{text}</Text>
    </View>
  );
  return onPress ? <Pressable onPress={onPress}>{body}</Pressable> : body;
}

export function SectionTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <View style={{ marginTop: 18, marginBottom: 8 }}>
      <Text style={s.sectionTitle}>{title}</Text>
      {hint ? <Text style={s.hint}>{hint}</Text> : null}
    </View>
  );
}

export const Loading = () => <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />;
export const Empty = ({ text }: { text: string }) => <Text style={s.empty}>{text}</Text>;
export const ErrorBox = ({ text, onRetry }: { text: string; onRetry?: () => void }) => (
  <Card>
    <Text style={{ color: Colors.danger, fontWeight: '600' }}>Couldn't load this</Text>
    <Text style={s.hint}>{text}</Text>
    {onRetry ? <Pressable onPress={onRetry}><Text style={{ color: Colors.primary, marginTop: 8, fontWeight: '600' }}>Try again</Text></Pressable> : null}
  </Card>
);

const s = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: 14, padding: 14, borderWidth: 1, borderColor: C.cardBorder, marginBottom: 10 },
  hero: { backgroundColor: C.surface, borderRadius: 18, padding: 18, borderWidth: 1, borderColor: C.cardBorder, marginBottom: 12 },
  heroBig: { color: C.text, fontSize: 40, fontWeight: '800' },
  heroLabel: { color: C.textSecondary, fontSize: 14, marginTop: 2 },
  heroSub: { color: C.textMuted, fontSize: 12, marginTop: 8, lineHeight: 17 },
  stat: { flex: 1, backgroundColor: C.card, borderRadius: 14, padding: 12, borderWidth: 1, borderColor: C.cardBorder },
  statLabel: { color: C.textMuted, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 },
  statValue: { fontSize: 22, fontWeight: '700', marginTop: 4 },
  statSub: { color: C.textMuted, fontSize: 11, marginTop: 2 },
  row: { flexDirection: 'row', gap: 10, marginBottom: 10 },
  pill: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 999, marginRight: 6, marginBottom: 6 },
  pillText: { fontSize: 12, fontWeight: '600' },
  sectionTitle: { color: C.text, fontSize: 16, fontWeight: '700' },
  hint: { color: C.textMuted, fontSize: 12, marginTop: 2 },
  empty: { color: C.textMuted, textAlign: 'center', marginTop: 30 },
});
