import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import Screen from '../../components/Screen';
import { Card, CardTitle, Empty, ErrorBox, Hero, Loading, Pill, Row, SectionTitle, Stat, ago, inr, minutesText, rupeesShort } from '../../components/ui';
import { useFilters } from '../../context/FilterContext';
import { apiClient, errorText } from '../../services/api';
import { Theme } from '../../constants/Colors';

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
  const [more, setMore] = useState(false);
  const outNow = d ? d.active - d.long_off : 0;
  const lostMid = loss?.high ? Math.round((loss.low + loss.high) / 2) : 0;
  const outNames = new Set<string>((d?.top_sellers_out?.items || []).map((i: any) => i.item_name));
  const fix: any[] = (loss?.items || []).slice(0, 5);

  return (
    <Screen title="Stock-outs" onRefresh={refetch} refreshing={summary.isRefetching}>
      {summary.isLoading ? <Loading /> : summary.error ? <ErrorBox text={errorText(summary.error)} onRetry={refetch} /> : d ? (
        <>
          <Card>
            <Text style={s.status}>
              {outNow ? <><Text style={s.b}>{outNow} dish{outNow === 1 ? '' : 'es'}</Text> {outNow === 1 ? 'is' : 'are'} out of stock right now, across <Text style={s.b}>{d.outlets_affected} outlet{d.outlets_affected === 1 ? '' : 's'}</Text>.</> : <><Text style={s.b}>Everything is available</Text> right now.</>}
            </Text>
            {lostMid ? <Text style={s.money}>Your best dishes being out of stock cost you about <Text style={s.b}>{rupeesShort(lostMid)}</Text> in sales in this period. <Text style={s.sub}>(an estimate)</Text></Text> : null}
            {fix.length ? (
              <View style={{ marginTop: 14 }}>
                <Text style={s.fixTitle}>Fix these first</Text>
                {fix.map((i: any, n: number) => (
                  <Text key={i.item_name} style={s.fixRow}>
                    {n + 1}. <Text style={s.b}>{i.item_name}</Text> <Text style={s.sub}>at {i.outlets} outlet{i.outlets === 1 ? '' : 's'} · lost about </Text><Text style={s.b}>{rupeesShort(Math.round((i.low + i.high) / 2))}</Text>{outNames.has(i.item_name) ? <Text style={s.nowTag}>  out now</Text> : null}
                  </Text>
                ))}
              </View>
            ) : null}
          </Card>
          <Pressable style={s.moreBtn} onPress={() => setMore(!more)}>
            <Text style={s.moreText}>{more ? 'Hide the details ▴' : 'See the details ▾'}</Text>
          </Pressable>
          {more ? (
        <>
          <Hero
            big={inr.format(d.active - d.long_off)}
            label="items out of stock right now"
            sub={`across ${d.outlets_affected} outlet${d.outlets_affected === 1 ? '' : 's'} · ${inr.format(d.restored)} back in stock · avg downtime ${minutesText(d.avg_downtime)}${d.long_off ? ` · ${inr.format(d.long_off)} more off ${d.long_off_days}+ days` : ''}`}
            tone={d.active - d.long_off > 0 ? 'bad' : 'normal'}
          />
          {loss?.high ? (
            <Card>
              <CardTitle label="Best sellers lost to stock-outs" title={`${rupeesShort(loss.low)} – ${rupeesShort(loss.high)}`} />
              <Text style={s.sub}>estimated sales lost in this period · only each stock-out's first 3 days count</Text>
              <View style={s.chips}>
                {(loss.items || []).slice(0, 8).map((i: any) => <Pill key={i.item_name} tone="red" text={`${i.item_name} · ${rupeesShort(i.low)}–${rupeesShort(i.high)}`} />)}
              </View>
            </Card>
          ) : null}
          {d.long_off_top_sellers?.length ? (
            <Card tint={Theme.cream}>
              <CardTitle label={`Off ${d.long_off_days}+ days`} title="Top sellers to check" />
              <Text style={s.sub}>Removed from the menu, or really out? Worth a call.</Text>
              <View style={s.chips}>
                {d.long_off_top_sellers.map((t: any) => <Pill key={t.item_name} tone="amber" text={`${t.item_name} · ${t.days}d`} />)}
              </View>
            </Card>
          ) : null}
          {d.stock_rejections?.orders ? (
            <Card>
              <CardTitle label="Orders turned away for stock" title={`${inr.format(d.stock_rejections.orders)} orders · ${rupeesShort(d.stock_rejections.value)}`} />
              <Text style={s.sub}>measured, not estimated</Text>
            </Card>
          ) : null}

          <SectionTitle title="By mealtime" hint="items out in this period, under the first meal each went out in" />
          <Row>{(d.by_meal || []).slice(0, 3).map((m: any) => <Stat key={m.meal} label={m.meal} value={String(m.count)} />)}</Row>
          <Row>{(d.by_meal || []).slice(3).map((m: any) => <Stat key={m.meal} label={m.meal} value={String(m.count)} />)}</Row>

          <SectionTitle title="Out now" hint={list.data ? `${list.data.length} shown` : undefined} />
          {list.isLoading ? <Loading /> : (list.data || []).length === 0 ? <Empty text="Nothing is out of stock right now." /> : (list.data || []).map((r: any) => (
            <Card key={r.id} style={{ paddingVertical: 12, borderRadius: 18, marginBottom: 8 }}>
              <Text style={s.item}>{r.item_name}</Text>
              <Text style={s.sub}>{r.outlet_name} · {r.platform} · out {ago(r.first_detected_at)}{r.mealtime ? ` · ${r.mealtime}` : ''}</Text>
            </Card>
          ))}
        </>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  status: { color: Theme.ink, fontSize: 20, lineHeight: 28 },
  money: { color: Theme.ink, fontSize: 15, lineHeight: 22, marginTop: 8 },
  b: { fontWeight: '800', color: Theme.ink },
  fixTitle: { color: Theme.ink, fontSize: 15, fontWeight: '800', marginBottom: 6 },
  fixRow: { color: Theme.ink, fontSize: 15, lineHeight: 24 },
  nowTag: { color: Theme.bad, fontSize: 11, fontWeight: '800' },
  moreBtn: { alignSelf: 'flex-start', backgroundColor: Theme.chip, borderRadius: 999, paddingHorizontal: 16, paddingVertical: 10, marginBottom: 12 },
  moreText: { color: Theme.white, fontWeight: '700', fontSize: 13 },
  sub: { color: Theme.inkMuted, fontSize: 12, marginTop: 3, lineHeight: 17 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 10 },
  item: { color: Theme.ink, fontSize: 15, fontWeight: '700' },
});
