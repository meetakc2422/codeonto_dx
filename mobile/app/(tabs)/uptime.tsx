import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import Screen from '../../components/Screen';
import { Card, Empty, ErrorBox, Hero, Loading, Pill, Row, SectionTitle, Stat, ago, minutesText } from '../../components/ui';
import { useFilters } from '../../context/FilterContext';
import { apiClient, errorText } from '../../services/api';
import { Theme } from '../../constants/Colors';

const colour = (v: number | null) => (v == null ? '#D1D5DB' : v >= 95 ? '#22C55E' : v >= 85 ? '#86EFAC' : v >= 70 ? '#F59E0B' : '#EF4444');

/** Store uptime: who is offline now, uptime for the period, a square per day, and what Zomato itself reports. */
export default function Uptime() {
  const { brand, params } = useFilters();
  const id = brand?.id;
  const q = useQuery({
    queryKey: ['uptime', id, params],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/uptime/summary`, { params })).data,
  });
  const d = q.data;
  const outlets: any[] = d?.outlets || [];
  const offline = outlets.filter((o) => o.offline_since);
  const days: string[] = [...new Set(outlets.flatMap((o) => Object.keys(o.days || {})))].sort() as string[];

  return (
    <Screen title="Uptime" onRefresh={() => q.refetch()} refreshing={q.isRefetching}>
      {q.isLoading ? <Loading /> : q.error ? <ErrorBox text={errorText(q.error)} onRetry={() => q.refetch()} /> : d ? (
        <>
          <Hero
            big={String(d.offline_now)}
            label={`outlet${d.offline_now === 1 ? '' : 's'} offline right now`}
            sub={`Zomato, during opening hours · ${d.last_checked_at ? `last checked ${ago(d.last_checked_at)}` : 'no checks yet'}`}
            tone={d.offline_now > 0 ? 'bad' : 'normal'}
          />
          <Row>
            <Stat label="Uptime" value={d.uptime_pct == null ? '—' : `${d.uptime_pct.toFixed(1)}%`} tone={d.uptime_pct != null && d.uptime_pct < 95 ? 'warn' : 'ok'} />
            <Stat label="Offline events" value={String(d.events)} />
            <Stat label="Avg downtime" value={minutesText(d.avg_downtime)} />
          </Row>

          {offline.length ? (
            <>
              <SectionTitle title="Offline now" />
              {offline.map((o) => (
                <Card key={o.id} tint={Theme.rose} style={{ borderRadius: 18, marginBottom: 8 }}>
                  <Text style={s.name}>{o.name} <Text style={s.city}>{o.city}</Text></Text>
                  <Text style={s.sub}>offline since {ago(o.offline_since)}</Text>
                </Card>
              ))}
            </>
          ) : null}

          <SectionTitle title="Outlets" hint="worst first · a square per day · Zomato's own offline hours in amber" />
          {outlets.length === 0 ? <Empty text="No uptime checks in this period." /> : outlets.slice(0, 60).map((o) => (
            <Card key={o.id} style={{ paddingVertical: 12, borderRadius: 18, marginBottom: 8 }}>
              <View style={s.top}>
                <Text style={s.name} numberOfLines={1}>{o.name} <Text style={s.city}>{o.city}</Text></Text>
                <Text style={[s.pct, { color: o.uptime_pct != null && o.uptime_pct < 85 ? Theme.bad : Theme.ink }]}>{o.uptime_pct == null ? '—' : `${o.uptime_pct.toFixed(1)}%`}</Text>
              </View>
              {days.length > 1 ? (
                <View style={s.cells}>
                  {days.map((day) => {
                    const v = (o.days || {})[day];
                    const zh = (o.zomato_days || {})[day];
                    const c = v == null && zh != null ? (zh >= 3 ? '#EF4444' : zh >= 0.5 ? '#F59E0B' : '#BBF7D0') : colour(v ?? null);
                    return <View key={day} style={[s.cell, { backgroundColor: c }]} />;
                  })}
                </View>
              ) : null}
              <View style={s.tags}>
                {o.offline_since ? <Pill tone="red" text="offline" /> : null}
                {o.zomato_hours ? <Pill tone="amber" text={`Zomato: ${o.zomato_hours.toFixed(1)} h offline`} /> : null}
                {o.events ? <Pill text={`${o.events} event${o.events === 1 ? '' : 's'} · ${minutesText(o.downtime_minutes)}`} /> : null}
              </View>
            </Card>
          ))}
        </>
      ) : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  name: { color: Theme.ink, fontSize: 15, fontWeight: '700', flexShrink: 1 },
  city: { color: Theme.inkMuted, fontSize: 12, fontWeight: '400' },
  sub: { color: Theme.inkMuted, fontSize: 12, marginTop: 3 },
  pct: { fontSize: 16, fontWeight: '800' },
  cells: { flexDirection: 'row', gap: 3, marginTop: 8, flexWrap: 'wrap' },
  cell: { width: 14, height: 14, borderRadius: 4 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 8 },
});
