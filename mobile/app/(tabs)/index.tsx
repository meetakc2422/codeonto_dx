import React, { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { ArrowUpRight } from 'lucide-react-native';
import Screen from '../../components/Screen';
import { Sparkline } from '../../components/charts';
import { Card, ErrorBox, Loading, Pill, inr, rupeesShort } from '../../components/ui';
import { useFilters } from '../../context/FilterContext';
import { apiClient, errorText } from '../../services/api';
import { Theme } from '../../constants/Colors';

type Point = { date: string; value: number };
const METRICS = { revenue: { code: 'gross_revenue', label: 'Revenue', fmt: (v: number) => rupeesShort(v) }, orders: { code: 'delivered_orders', label: 'Orders', fmt: (v: number) => inr.format(Math.round(v)) } };
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const pct = (now: number, before: number) => (before ? Math.round((100 * (now - before)) / before) : null);
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function group(points: Point[], key: (d: Date) => string) {
  const m = new Map<string, number>();
  points.forEach((p) => { const k = key(new Date(`${p.date}T00:00:00`)); m.set(k, (m.get(k) || 0) + p.value); });
  return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
}
const weekKey = (d: Date) => { const x = new Date(d); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return iso(x); };

function Change({ now, before }: { now: number; before: number }) {
  const p = pct(now, before);
  if (p == null) return null;
  return <Text style={[s.change, { color: p >= 0 ? Theme.good : Theme.bad }]}>{p >= 0 ? '▲' : '▼'} {Math.abs(p)}% vs before</Text>;
}

/** Insights: the day, the week, the month and the weekday pattern of revenue or orders, each as a tinted card with its trend. */
export default function Insights() {
  const { brand, params } = useFilters();
  const id = brand?.id;
  const [metric, setMetric] = useState<keyof typeof METRICS>('revenue');
  const [open, setOpen] = useState<string>('');
  const m = METRICS[metric];
  const range = useMemo(() => { const end = new Date(), start = new Date(); start.setDate(end.getDate() - 180); return { start: iso(start), end: iso(end) }; }, []);
  const q = useQuery<Point[]>({
    queryKey: ['trend', id, metric, params.platform, range],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/kpis/${m.code}/trend`, { params: { ...range, ...(params.platform ? { platform: params.platform } : {}) } })).data,
  });

  const cards = useMemo(() => {
    const pts = (q.data || []).filter((p) => p.value != null);
    if (pts.length < 2) return null;
    const daily = pts.slice(-14);
    const weekly = group(pts, weekKey).slice(-9);
    const monthly = group(pts, (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`).slice(-6);
    const byDay = DAYS.map((_, i) => { const v = pts.filter((p) => (new Date(`${p.date}T00:00:00`).getDay() + 6) % 7 === i).map((p) => p.value); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : 0; });
    return { daily, weekly, monthly, byDay };
  }, [q.data]);

  const last = <T,>(a: T[], n = 1) => a[a.length - n];

  return (
    <Screen title="Insights" onRefresh={() => q.refetch()} refreshing={q.isRefetching}>
      <View style={{ flexDirection: 'row', marginBottom: 12 }}>
        {(Object.keys(METRICS) as (keyof typeof METRICS)[]).map((k) => <Pill key={k} dark text={METRICS[k].label} active={metric === k} onPress={() => setMetric(k)} />)}
      </View>
      {q.isLoading ? <Loading /> : q.error ? <ErrorBox text={errorText(q.error)} onRetry={() => q.refetch()} /> : !cards ? <Text style={s.empty}>Not enough data yet.</Text> : (
        <>
          <Pressable onPress={() => setOpen(open === 'daily' ? '' : 'daily')}>
            <Card tint={Theme.mint}>
              <View style={s.head}><Text style={s.title}>Daily Insights</Text><ArrowUpRight size={18} color={Theme.ink} /></View>
              <Text style={s.value}>{m.fmt(last(cards.daily).value)} <Text style={s.small}>yesterday-ish · {last(cards.daily).date.slice(5)}</Text></Text>
              <Change now={last(cards.daily).value} before={last(cards.daily, 2).value} />
              <Sparkline values={cards.daily.map((p) => p.value)} color={Theme.mintLine} />
              {open === 'daily' ? cards.daily.slice().reverse().map((p) => <View key={p.date} style={s.line}><Text style={s.lineL}>{p.date}</Text><Text style={s.lineR}>{m.fmt(p.value)}</Text></View>) : <Text style={s.tap}>Tap to view the last 14 days</Text>}
            </Card>
          </Pressable>

          <Pressable onPress={() => setOpen(open === 'weekly' ? '' : 'weekly')}>
            <Card tint={Theme.cream}>
              <View style={s.head}><Text style={s.title}>Weekly Insights</Text><ArrowUpRight size={18} color={Theme.ink} /></View>
              <Text style={s.value}>{m.fmt(last(cards.weekly, 2)[1])} <Text style={s.small}>last full week</Text></Text>
              <Change now={last(cards.weekly, 2)[1]} before={last(cards.weekly, 3)?.[1] ?? 0} />
              <Sparkline values={cards.weekly.map(([, v]) => v)} color={Theme.creamLine} />
              {open === 'weekly' ? cards.weekly.slice().reverse().map(([k, v], i) => <View key={k} style={s.line}><Text style={s.lineL}>Week of {k.slice(5)}{i === 0 ? ' (so far)' : ''}</Text><Text style={s.lineR}>{m.fmt(v)}</Text></View>) : <Text style={s.tap}>Tap to view the last 9 weeks</Text>}
            </Card>
          </Pressable>

          <Pressable onPress={() => setOpen(open === 'monthly' ? '' : 'monthly')}>
            <Card tint={Theme.sky}>
              <View style={s.head}><Text style={s.title}>Monthly Insights</Text><ArrowUpRight size={18} color={Theme.ink} /></View>
              <Text style={s.value}>{m.fmt(last(cards.monthly)[1])} <Text style={s.small}>this month so far</Text></Text>
              <Sparkline values={cards.monthly.map(([, v]) => v)} color={Theme.skyLine} />
              {open === 'monthly' ? cards.monthly.slice().reverse().map(([k, v]) => <View key={k} style={s.line}><Text style={s.lineL}>{k}</Text><Text style={s.lineR}>{m.fmt(v)}</Text></View>) : <Text style={s.tap}>Tap to view the last 6 months</Text>}
            </Card>
          </Pressable>

          <Pressable onPress={() => setOpen(open === 'dow' ? '' : 'dow')}>
            <Card tint={Theme.rose}>
              <View style={s.head}><Text style={s.title}>Day wise Insights</Text><ArrowUpRight size={18} color={Theme.ink} /></View>
              <Text style={s.value}>{DAYS[cards.byDay.indexOf(Math.max(...cards.byDay))]} <Text style={s.small}>is your best day</Text></Text>
              <Sparkline values={cards.byDay} color={Theme.roseLine} />
              {open === 'dow' ? DAYS.map((d, i) => <View key={d} style={s.line}><Text style={s.lineL}>{d}</Text><Text style={s.lineR}>{m.fmt(cards.byDay[i])} avg</Text></View>) : <Text style={s.tap}>Tap to view the average for each weekday</Text>}
            </Card>
          </Pressable>
        </>
      )}
    </Screen>
  );
}

const s = StyleSheet.create({
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { color: Theme.ink, fontSize: 22, fontWeight: '800' },
  value: { color: Theme.ink, fontSize: 28, fontWeight: '800', marginTop: 8 },
  small: { fontSize: 12, fontWeight: '500', color: Theme.inkMuted },
  change: { fontSize: 12, fontWeight: '700', marginTop: 2, marginBottom: 4 },
  tap: { color: Theme.inkMuted, fontSize: 12, marginTop: 4 },
  line: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: 'rgba(0,0,0,0.07)' },
  lineL: { color: Theme.ink, fontSize: 13 },
  lineR: { color: Theme.ink, fontSize: 13, fontWeight: '700' },
  empty: { color: Theme.whiteMuted, textAlign: 'center', marginTop: 30 },
});
