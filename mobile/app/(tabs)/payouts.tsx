import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import Screen from '../../components/Screen';
import { Card, Empty, ErrorBox, Loading, Pill, Row, SectionTitle, Stat, inr, rupees, rupeesShort, shortDate } from '../../components/ui';
import { useFilters } from '../../context/FilterContext';
import { apiClient, errorText } from '../../services/api';
import { Colors } from '../../constants/Colors';

const C = Colors.dark;
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
    <View style={{ marginTop: 10 }}>
      {d.issues?.length ? d.issues.map((c: string) => <Text key={c} style={s.issue}>• {d.issue_labels?.[c] || c}</Text>) : null}
      {(d.breakdown || []).map((sec: any) => (
        <View key={sec.id || sec.label} style={s.line}>
          <Text style={s.lineLabel}>{sec.label}</Text>
          <Text style={s.lineValue}>{rupees(sec.value)}{base && base.value ? `  ${(100 * Math.abs(sec.value) / Math.abs(base.value)).toFixed(1)}%` : ''}</Text>
        </View>
      ))}
      <View style={[s.line, { borderTopWidth: 1, borderTopColor: C.cardBorder, marginTop: 6, paddingTop: 6 }]}>
        <Text style={[s.lineLabel, { fontWeight: '700' }]}>Net payout</Text>
        <Text style={[s.lineValue, { fontWeight: '700' }]}>{rupees(d.net_payout)}</Text>
      </View>
      {d.reconciled ? (
        <View style={{ marginTop: 10 }}>
          <View style={s.line}><Text style={s.lineLabel}>Our check: expected payout</Text><Text style={s.lineValue}>{rupees(d.expected_payout)}</Text></View>
          <View style={s.line}><Text style={s.lineLabel}>Difference</Text><Text style={[s.lineValue, { color: d.issues?.includes('payout_mismatch') ? Colors.danger : Colors.success }]}>{rupees(d.discrepancy)}</Text></View>
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
    <Screen onRefresh={refetch} refreshing={list.isRefetching}>
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
            <Card style={{ borderColor: 'rgba(239,68,68,0.4)' }}>
              <Text style={s.label}>Unexplained difference</Text>
              <Text style={[s.big, { color: Colors.danger }]}>{rupeesShort(Math.abs(d.discrepancy_total))}</Text>
              <Text style={s.sub}>between what Zomato or Swiggy paid and what the orders say they should have paid</Text>
            </Card>
          ) : null}
          {d.issues?.length ? (
            <>
              <SectionTitle title="What needs checking" />
              {d.issues.map((i: any) => <Text key={i.code} style={s.issue}>• {i.count} · {i.label}</Text>)}
            </>
          ) : null}
        </>
      ) : null}

      <SectionTitle title="Payouts" />
      <View style={s.chips}>
        {([['', 'All'], ['issues', 'To check'], ['paid', 'Paid'], ['to_be_paid', 'To be paid']] as [Status, string][]).map(([v, l]) => <Pill key={v || 'all'} text={l} active={status === v} onPress={() => setStatus(v)} />)}
      </View>
      {list.isLoading ? <Loading /> : list.error ? <ErrorBox text={errorText(list.error)} onRetry={refetch} /> : rows.length === 0 ? <Empty text="No payouts for these dates." /> : rows.map((c) => (
        <Card key={c.id}>
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
      {list.data && list.data.total > rows.length ? <Text style={s.sub}>Showing {rows.length} of {inr.format(list.data.total)}. Choose a shorter period to see the rest.</Text> : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 8 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  name: { color: C.text, fontSize: 15, fontWeight: '600', flexShrink: 1 },
  city: { color: C.textMuted, fontSize: 12, fontWeight: '400' },
  amount: { color: C.text, fontSize: 16, fontWeight: '700' },
  sub: { color: C.textMuted, fontSize: 12, marginTop: 3, lineHeight: 17 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 8 },
  label: { color: C.textMuted, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 },
  big: { fontSize: 24, fontWeight: '800', marginTop: 4 },
  issue: { color: C.textSecondary, fontSize: 13, marginBottom: 4 },
  line: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 3 },
  lineLabel: { color: C.textSecondary, fontSize: 13, flex: 1, paddingRight: 8 },
  lineValue: { color: C.text, fontSize: 13 },
});
