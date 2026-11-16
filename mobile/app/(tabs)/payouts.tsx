import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import Screen from '../../components/Screen';
import { Card, CardTitle, Empty, ErrorBox, Loading, Pill, Row, SectionTitle, Stat, inr, rupees, rupeesShort, shortDate } from '../../components/ui';
import { useFilters } from '../../context/FilterContext';
import { apiClient, errorText } from '../../services/api';
import { Theme } from '../../constants/Colors';

type Status = '' | 'issues' | 'paid' | 'to_be_paid';

function Detail({ brandId, cycleId }: { brandId: number; cycleId: number }) {
  const q = useQuery({
    queryKey: ['cycle', brandId, cycleId],
    queryFn: async () => (await apiClient.get(`/brands/${brandId}/payouts/cycles/${cycleId}`)).data,
  });
  if (q.isLoading) return <Loading />;
  if (q.error || !q.data) return <Text style={s.sub}>{errorText(q.error)}</Text>;
  const d = q.data;
  const base = (d.breakdown || []).find((x: any) => /^net order value/i.test(x.label || ''));
  return (
    <View style={{ marginTop: 12 }}>
      {d.issues?.length ? d.issues.map((c: string) => <Text key={c} style={s.issue}>• {d.issue_labels?.[c] || c}</Text>) : null}
      {(d.breakdown || []).map((sec: any) => (
        <View key={sec.id || sec.label} style={s.line}>
          <Text style={s.lineLabel}>{sec.label}</Text>
          <Text style={s.lineValue}>{rupees(sec.value)}{base && base.value ? `  ${(100 * Math.abs(sec.value) / Math.abs(base.value)).toFixed(1)}%` : ''}</Text>
        </View>
      ))}
      <View style={[s.line, { borderTopWidth: 1, borderTopColor: Theme.line, marginTop: 6, paddingTop: 8 }]}>
        <Text style={[s.lineLabel, { fontWeight: '800' }]}>Net payout</Text>
        <Text style={[s.lineValue, { fontWeight: '800' }]}>{rupees(d.net_payout)}</Text>
      </View>
      {d.reconciled ? (
        <View style={{ marginTop: 10 }}>
          <View style={s.line}><Text style={s.lineLabel}>Our check: expected payout</Text><Text style={s.lineValue}>{rupees(d.expected_payout)}</Text></View>
          <View style={s.line}><Text style={s.lineLabel}>Difference</Text><Text style={[s.lineValue, { color: d.issues?.includes('payout_mismatch') ? Theme.bad : Theme.good }]}>{rupees(d.discrepancy)}</Text></View>
        </View>
      ) : <Text style={[s.sub, { marginTop: 8 }]}>Orders are checked once this payout is paid.</Text>}
    </View>
  );
}

/** Reconciliation: how many payouts need a look, then each payout with its statement and our check. */
export default function Payouts() {
  const { brand, params } = useFilters();
  const id = brand?.id;
  const [status, setStatus] = useState<Status>('');
  const [open, setOpen] = useState<number | null>(null);
  const summary = useQuery({
    queryKey: ['pay-summary', id, params],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/payouts/summary`, { params })).data,
  });
  const list = useQuery({
    queryKey: ['pay-list', id, params, status],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/payouts/cycles`, { params: { ...params, limit: 60, ...(status ? { status } : {}) } })).data,
  });
  const d = summary.data;
  const refetch = () => { summary.refetch(); list.refetch(); };
  const rows: any[] = list.data?.results || [];

  return (
    <Screen title="Payouts" onRefresh={refetch} refreshing={list.isRefetching}>
      {summary.isLoading ? <Loading /> : summary.error ? <ErrorBox text={errorText(summary.error)} onRetry={refetch} /> : d ? (
        <>
          <Row>
            <Stat label="Payouts" value={inr.format(d.cycles)} sub={`${d.reconciled} checked`} />
            <Stat label="To check" value={String(d.with_issues)} tone={d.with_issues ? 'bad' : 'ok'} />
          </Row>
          <Row>
            <Stat label="Paid" value={rupeesShort(d.paid_total)} />
            <Stat label="To be paid" value={rupeesShort(d.to_be_paid_total)} sub={`${d.to_be_paid_cycles} cycles`} />
          </Row>
          {d.discrepancy_total ? (
            <Card tint={Theme.rose}>
              <CardTitle label="Unexplained difference" title={rupeesShort(Math.abs(d.discrepancy_total))} />
              <Text style={s.sub}>between what Zomato or Swiggy paid and what the orders say they should have paid</Text>
            </Card>
          ) : null}
          {d.issues?.length ? (
            <Card>
              <CardTitle title="What needs checking" />
              {d.issues.map((i: any) => <Text key={i.code} style={s.issue}>• {i.count} · {i.label}</Text>)}
            </Card>
          ) : null}
        </>
      ) : null}

      <SectionTitle title="Payouts" />
      <View style={s.chips}>
        {([['', 'All'], ['issues', 'To check'], ['paid', 'Paid'], ['to_be_paid', 'To be paid']] as [Status, string][]).map(([v, l]) => <Pill key={v || 'all'} dark text={l} active={status === v} onPress={() => setStatus(v)} />)}
      </View>
      {list.isLoading ? <Loading /> : list.error ? <ErrorBox text={errorText(list.error)} onRetry={refetch} /> : rows.length === 0 ? <Empty text="No payouts for these dates." /> : rows.map((c) => (
        <Card key={c.id} style={{ borderRadius: 20, marginBottom: 8 }}>
          <Pressable onPress={() => setOpen(open === c.id ? null : c.id)}>
            <View style={s.top}>
              <Text style={s.name} numberOfLines={1}>{c.outlet} <Text style={s.city}>{c.city}</Text></Text>
              <Text style={s.amount}>{rupees(c.net_payout)}</Text>
            </View>
            <Text style={s.sub}>{c.platform === 'swiggy' ? 'Swiggy' : 'Zomato'} · {shortDate(c.start_date)}{c.end_date !== c.start_date ? ` – ${shortDate(c.end_date)}` : ''} · {c.order_count} orders · pays {shortDate(c.payout_date)}</Text>
            <View style={s.tags}>
              <Pill tone={/^paid$/i.test(c.status) ? 'green' : 'amber'} text={c.status} />
              {c.issues?.length ? <Pill tone="red" text={`${c.issues.length} to check`} /> : c.reconciled ? <Pill tone="green" text="matches" /> : null}
              {c.utr ? <Pill text={`UTR ${c.utr}`} /> : null}
            </View>
          </Pressable>
          {open === c.id && id ? <Detail brandId={id} cycleId={c.id} /> : null}
        </Card>
      ))}
      {list.data && list.data.total > rows.length ? <Text style={[s.sub, { color: Theme.whiteMuted }]}>Showing {rows.length} of {inr.format(list.data.total)}. Choose a shorter period to see the rest.</Text> : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 8 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  name: { color: Theme.ink, fontSize: 15, fontWeight: '700', flexShrink: 1 },
  city: { color: Theme.inkMuted, fontSize: 12, fontWeight: '400' },
  amount: { color: Theme.ink, fontSize: 16, fontWeight: '800' },
  sub: { color: Theme.inkMuted, fontSize: 12, marginTop: 3, lineHeight: 17 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 8 },
  issue: { color: Theme.ink, fontSize: 13, marginBottom: 4 },
  line: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 3 },
  lineLabel: { color: Theme.inkMuted, fontSize: 13, flex: 1, paddingRight: 8 },
  lineValue: { color: Theme.ink, fontSize: 13 },
});
