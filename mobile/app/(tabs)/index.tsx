import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import Screen from '../../components/Screen';
import { Card, Empty, ErrorBox, Hero, Loading, Pill, Row, SectionTitle, Stat, ago, inr, minutesText, rupeesShort } from '../../components/ui';
import { useFilters } from '../../context/FilterContext';
import { apiClient, errorText } from '../../services/api';
import { Colors } from '../../constants/Colors';

const C = Colors.dark;

/** Stock-outs: what is out right now, what it is costing, which meal times it hits, and the items themselves. */
export default function StockOuts() {
  const { brand, params } = useFilters();
  const id = brand?.id;
  const summary = useQuery({
    queryKey: ['so-summary', id, params],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/stock-outs/summary`, { params })).data,
  });
  const list = useQuery({
    queryKey: ['so-list', id, params],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/stock-outs`, { params: { ...params, status: 'active', limit: 60 } })).data as any[],
  });
  const refetch = () => { summary.refetch(); list.refetch(); };
  const d = summary.data;
  const loss = d?.period_loss;

  return (
    <Screen onRefresh={refetch} refreshing={summary.isRefetching}>
      {summary.isLoading ? <Loading /> : summary.error ? <ErrorBox text={errorText(summary.error)} onRetry={refetch} /> : d ? (
        <>
          <Hero
            big={inr.format(d.active - d.long_off)}
            label="items out of stock right now"
            sub={`across ${d.outlets_affected} outlet${d.outlets_affected === 1 ? '' : 's'} · ${inr.format(d.restored)} back in stock · avg downtime ${minutesText(d.avg_downtime)}${d.long_off ? ` · ${inr.format(d.long_off)} more off ${d.long_off_days}+ days` : ''}`}
            tone={d.active - d.long_off > 0 ? 'bad' : 'normal'}
          />
          {loss?.high ? (
            <Card>
              <Text style={s.cardLabel}>Best sellers lost to stock-outs</Text>
              <Text style={s.money}>{rupeesShort(loss.low)} – {rupeesShort(loss.high)}</Text>
              <Text style={s.sub}>estimated sales lost in this period · only each stock-out's first 3 days count</Text>
              <View style={s.chips}>
                {(loss.items || []).slice(0, 8).map((i: any) => <Pill key={i.item_name} tone="red" text={`${i.item_name} · ${rupeesShort(i.low)}–${rupeesShort(i.high)}`} />)}
              </View>
            </Card>
          ) : null}
          {d.long_off_top_sellers?.length ? (
            <Card>
              <Text style={s.cardLabel}>Top sellers off {d.long_off_days}+ days</Text>
              <Text style={s.sub}>Removed from the menu, or really out? Worth a call.</Text>
              <View style={s.chips}>
                {d.long_off_top_sellers.map((t: any) => <Pill key={t.item_name} tone="amber" text={`${t.item_name} · ${t.days}d`} />)}
              </View>
            </Card>
          ) : null}
          {d.stock_rejections?.orders ? (
            <Card>
              <Text style={s.cardLabel}>Orders turned away for stock</Text>
              <Text style={s.money}>{inr.format(d.stock_rejections.orders)} orders · {rupeesShort(d.stock_rejections.value)}</Text>
              <Text style={s.sub}>measured, not estimated</Text>
            </Card>
          ) : null}

          <SectionTitle title="By mealtime" hint="items out in this period, under the first meal each went out in" />
          <Row>
            {(d.by_meal || []).slice(0, 3).map((m: any) => <Stat key={m.meal} label={m.meal} value={String(m.count)} />)}
          </Row>
          <Row>
            {(d.by_meal || []).slice(3).map((m: any) => <Stat key={m.meal} label={m.meal} value={String(m.count)} />)}
          </Row>

          <SectionTitle title="Out now" hint={list.data ? `${list.data.length} shown, newest first` : undefined} />
          {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty text="Nothing is out of stock right now." /> : (list.data || []).map((r: any) => (
            <Card key={r.id} style={{ paddingVertical: 10 }}>
              <Text style={s.item}>{r.item_name}</Text>
              <Text style={s.sub}>{r.outlet_name} · {r.platform} · out {ago(r.first_detected_at)}{r.mealtime ? ` · ${r.mealtime}` : ''}</Text>
            </Card>
          ))}
        </>
      ) : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  cardLabel: { color: C.textMuted, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 },
  money: { color: C.text, fontSize: 24, fontWeight: '800', marginTop: 4 },
  sub: { color: C.textMuted, fontSize: 12, marginTop: 3, lineHeight: 17 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 10 },
  item: { color: C.text, fontSize: 15, fontWeight: '600' },
});
