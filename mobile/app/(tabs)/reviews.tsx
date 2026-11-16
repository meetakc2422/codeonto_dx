import React, { useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Screen from '../../components/Screen';
import { Bars, Donut } from '../../components/charts';
import { Card, CardTitle, Empty, ErrorBox, Loading, Pill, SectionTitle, ago } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import { useFilters } from '../../context/FilterContext';
import { apiClient, errorText } from '../../services/api';
import { Colors, Theme } from '../../constants/Colors';

type Filter = '' | 'pending' | 'neg';

/** A reply to start from, matched to the stars. Staff edit it before sending. */
function suggest(r: any, brand: string) {
  const first = (r.author_name || '').trim().split(/\s+/)[0];
  const hi = first && !/^(anonymous|zomato|swiggy|customer|guest)$/i.test(first) ? `Hi ${first}` : 'Hi there';
  const sign = `\n\nWarm regards,\nTeam ${brand}`;
  const stars = r.rating != null ? Math.round(r.rating) : null;
  if (stars == null || stars >= 4) return `${hi}, thank you so much for the ${stars ? `${stars}-star rating` : 'kind words'}! We are delighted you enjoyed your order and look forward to serving you again soon.${sign}`;
  if (stars === 3) return `${hi}, thank you for your feedback. We are sorry your experience was not perfect. We have shared your comments with our team so we can improve, and we would love another chance to serve you better.${sign}`;
  return `${hi}, we are sorry your order did not meet your expectations. We would like to understand what went wrong and make it right, so please reach out to us. We would love another chance to serve you better.${sign}`;
}

function ReviewCard({ r, brandName, canEdit }: { r: any; brandName: string; canEdit: boolean }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const canReply = canEdit && r.reply_status !== 'replied' && !r.queued;
  const send = useMutation({
    mutationFn: async (now: boolean) => (await apiClient.post(`/reviews/${r.id}/replies`, { body: text.trim(), ...(now ? { send: true } : {}) })).data,
    onSuccess: (res, now) => {
      qc.invalidateQueries({ queryKey: ['reviews'] });
      qc.invalidateQueries({ queryKey: ['reviews-summary'] });
      Alert.alert(now ? (res.sent ? 'Posted to Zomato' : 'Queued') : 'Draft saved', now && !res.sent ? 'It will be posted to Zomato shortly.' : undefined);
      setOpen(false);
    },
    onError: (e) => Alert.alert("Couldn't send", errorText(e)),
  });
  const tone = r.rating != null && r.rating <= 2 ? Theme.bad : r.rating === 3 ? Theme.warn : Theme.good;
  return (
    <Card style={{ borderRadius: 20, marginBottom: 8 }}>
      <Pressable onPress={() => { setOpen(!open); if (!open && !text) setText(suggest(r, brandName)); }}>
        <View style={s.top}>
          <Text style={[s.stars, { color: tone }]}>{r.rating == null ? '—' : `${r.rating}★`}</Text>
          <Text style={s.meta} numberOfLines={1}>{r.outlet_name?.split(' · ').pop()} · {r.platform} · {ago(r.reviewed_at)}</Text>
          <Pill tone={r.reply_status === 'replied' ? 'green' : 'amber'} text={r.queued ? 'queued' : r.reply_status} />
        </View>
        <Text style={s.body} numberOfLines={open ? undefined : 3}>{r.body || 'Rating only, no text'}</Text>
        <Text style={s.author}>{r.author_name || 'Anonymous'}</Text>
      </Pressable>
      {r.latest_reply ? <View style={s.reply}><Text style={s.replyText}>{r.latest_reply}</Text></View> : null}
      {open && canReply ? (
        <View style={{ marginTop: 10 }}>
          <Text style={s.hint}>Suggested reply: edit it before you send.</Text>
          <TextInput style={s.input} multiline value={text} onChangeText={setText} placeholder="Write a reply…" placeholderTextColor={Theme.inkMuted} />
          <View style={s.actions}>
            <Pressable style={[s.btn, s.btnLight]} disabled={send.isPending || !text.trim()} onPress={() => send.mutate(false)}><Text style={s.btnLightText}>Save draft</Text></Pressable>
            {r.send_mode ? (
              <Pressable
                style={[s.btn, (send.isPending || !text.trim()) && { opacity: 0.5 }]}
                disabled={send.isPending || !text.trim()}
                onPress={() => Alert.alert('Send to Zomato now?', "Once it is posted it can't be edited here.", [{ text: 'Cancel', style: 'cancel' }, { text: 'Send', onPress: () => send.mutate(true) }])}
              >
                <Text style={s.btnText}>{send.isPending ? 'Sending…' : 'Send to Zomato'}</Text>
              </Pressable>
            ) : null}
          </View>
        </View>
      ) : null}
    </Card>
  );
}

function Segmented<T extends string>({ options, value, onChange }: { options: [T, string][]; value: T; onChange: (v: T) => void }) {
  return (
    <View style={s.seg}>
      {options.map(([v, l]) => (
        <Pressable key={v} style={[s.segItem, value === v && { backgroundColor: Theme.lime }]} onPress={() => onChange(v)}>
          <Text style={[s.segText, value === v && { color: Theme.ink }]}>{l}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export default function Reviews() {
  const { brand, params } = useFilters();
  const { user } = useAuth();
  const id = brand?.id;
  const [view, setView] = useState<'store' | 'item'>('store');
  const [filter, setFilter] = useState<Filter>('pending');
  const summary = useQuery({
    queryKey: ['reviews-summary', id, params],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/reviews/summary`, { params })).data,
  });
  const outlets = useQuery({
    queryKey: ['outlet-names', id],
    enabled: !!id,
    queryFn: async () => Object.fromEntries(((await apiClient.get(`/brands/${id}/outlets`)).data.outlets || []).map((o: any) => [o.id, o.area || o.outlet_name])),
  });
  const items = useQuery({
    queryKey: ['items', id, params],
    enabled: !!id && view === 'item',
    queryFn: async () => (await apiClient.get(`/brands/${id}/items`, { params })).data,
  });
  const list = useQuery({
    queryKey: ['reviews', id, params, filter],
    enabled: !!id && view === 'store',
    queryFn: async () => (await apiClient.get(`/brands/${id}/reviews`, {
      params: { ...params, limit: 40, ...(filter === 'pending' ? { reply_status: 'pending' } : {}), ...(filter === 'neg' ? { rating: 'neg' } : {}) },
    })).data as any[],
  });
  const d = summary.data;
  const names: Record<number, string> = outlets.data || {};
  const refetch = () => { summary.refetch(); list.refetch(); items.refetch(); };
  const stars = (n: number) => (d?.by_rating || []).filter((r: any) => (n === 3 ? r.stars === 3 : n === 5 ? r.stars >= 4 : r.stars <= 2)).reduce((t: number, r: any) => t + r.count, 0);
  const pos = d ? stars(5) : 0, neu = d ? stars(3) : 0, neg = d ? stars(1) : 0;
  const rated = ((items.data?.items || []) as any[]).filter((i) => i.avg_item_rating != null && i.rated >= 5).sort((a, b) => a.avg_item_rating - b.avg_item_rating);

  return (
    <Screen title="Reviews" onRefresh={refetch} refreshing={summary.isRefetching}>
      <Segmented options={[['store', 'Store'], ['item', 'Item']]} value={view} onChange={setView} />
      {summary.isLoading ? <Loading /> : summary.error ? <ErrorBox text={errorText(summary.error)} onRetry={refetch} /> : d ? (
        view === 'store' ? (
          <>
            <Card>
              <CardTitle label="Sentiment Overview" title="Overview of Customer feedback" />
              <View style={s.sent}>
                <View style={{ gap: 8 }}>
                  <Pill tone="green" text={`Positive  ${pos}`} />
                  <Pill tone="amber" text={`Neutral  ${neu}`} />
                  <Pill tone="red" text={`Negative  ${neg}`} />
                </View>
                <Donut center={String(d.total)} parts={[{ value: pos, color: '#A7F3D0' }, { value: neu, color: '#FDE68A' }, { value: neg, color: '#FCA5A5' }]} />
              </View>
              <Text style={s.hint}>4–5★ positive · 3★ neutral · 1–2★ negative · average {d.avg_rating ? `${d.avg_rating.toFixed(2)}★` : '—'} · {d.pending} to reply</Text>
            </Card>

            <Card>
              <CardTitle label="Page Ratings" title="Platform wise store ratings" />
              <Bars items={(d.by_platform || []).filter((p: any) => p.avg_rating != null).map((p: any) => ({ label: p.platform === 'zomato' ? 'Zomato' : p.platform === 'swiggy' ? 'Swiggy' : 'Google', value: p.avg_rating, color: p.platform === 'zomato' ? Colors.zomato : p.platform === 'swiggy' ? Colors.swiggy : '#4285F4' }))} />
            </Card>

            <SectionTitle title="Outlets to look at" hint="most 1–2★ reviews first" />
            {(d.by_outlet || []).slice(0, 8).map((o: any) => (
              <Card key={o.outlet_id} style={{ paddingVertical: 12, borderRadius: 18, marginBottom: 8 }}>
                <View style={s.top}>
                  <Text style={s.name} numberOfLines={1}>{names[o.outlet_id] || `Outlet ${o.outlet_id}`}</Text>
                  <Text style={[s.rate, { color: o.avg_rating && o.avg_rating < 3.5 ? Theme.bad : Theme.ink }]}>{o.avg_rating ? `${o.avg_rating.toFixed(2)}★` : '—'}</Text>
                </View>
                <Text style={s.hint}>{o.count} reviews · {o.negative} at 1–2★ · {o.pending} to reply</Text>
              </Card>
            ))}

            <SectionTitle title="What customers talk about" hint="reviews mentioning each topic · 1–2★ in red" />
            <View style={s.chips}>
              {(d.by_topic?.topics || []).filter((t: any) => t.count).sort((a: any, b: any) => b.count - a.count).slice(0, 8).map((t: any) => (
                <Pill key={t.slug} tone={t.negative ? 'red' : 'grey'} text={`${t.label} ${t.count}${t.negative ? ` · ${t.negative}` : ''}`} />
              ))}
            </View>

            <SectionTitle title="Reviews" />
            <View style={s.chips}>
              {([['pending', 'To reply'], ['neg', '1–2★'], ['', 'All']] as [Filter, string][]).map(([v, l]) => <Pill key={v || 'all'} dark text={l} active={filter === v} onPress={() => setFilter(v)} />)}
            </View>
            {list.isLoading ? <Loading /> : list.error ? <ErrorBox text={errorText(list.error)} onRetry={refetch} /> :
              (list.data || []).length === 0 ? <Empty text="No reviews here." /> :
              (list.data || []).map((r) => <ReviewCard key={r.id} r={r} brandName={brand?.name?.replace(/\b\w/g, (c) => c.toUpperCase()) || ''} canEdit={user?.can_edit !== false} />)}
          </>
        ) : (
          <>
            <SectionTitle title="Dish ratings" hint="from dish feedback in reviews · lowest rated first · dishes with 5 or more ratings" />
            {items.isLoading ? <Loading /> : items.error ? <ErrorBox text={errorText(items.error)} onRetry={refetch} /> : rated.length === 0 ? <Empty text="Not enough dish ratings in this period." /> : rated.slice(0, 40).map((i: any) => (
              <Card key={i.name} style={{ paddingVertical: 12, borderRadius: 18, marginBottom: 8 }}>
                <View style={s.top}>
                  <Text style={s.name} numberOfLines={1}>{i.name}</Text>
                  <Text style={[s.rate, { color: i.avg_item_rating < 3.5 ? Theme.bad : i.avg_item_rating >= 4.2 ? Theme.good : Theme.ink }]}>{i.avg_item_rating.toFixed(1)}★</Text>
                </View>
                <Text style={s.hint}>{i.rated} ratings · {i.bad_review_pct}% at 1–2★ · {i.complaints} complaints · {i.outlets} outlets</Text>
              </Card>
            ))}
          </>
        )
      ) : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  seg: { flexDirection: 'row', backgroundColor: Theme.chip, borderRadius: 999, padding: 4, marginBottom: 14 },
  segItem: { flex: 1, alignItems: 'center', paddingVertical: 10, borderRadius: 999 },
  segText: { color: Theme.whiteMuted, fontWeight: '800', fontSize: 14 },
  sent: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginVertical: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 8 },
  top: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6, justifyContent: 'space-between' },
  stars: { fontSize: 15, fontWeight: '800' },
  meta: { color: Theme.inkMuted, fontSize: 12, flex: 1 },
  name: { color: Theme.ink, fontSize: 15, fontWeight: '700', flex: 1 },
  rate: { fontSize: 16, fontWeight: '800' },
  body: { color: Theme.ink, fontSize: 14, lineHeight: 20 },
  author: { color: Theme.inkMuted, fontSize: 12, marginTop: 6 },
  reply: { marginTop: 10, borderLeftWidth: 3, borderLeftColor: Theme.lime, paddingLeft: 10 },
  replyText: { color: Theme.inkMuted, fontSize: 13, lineHeight: 18 },
  hint: { color: Theme.inkMuted, fontSize: 12, marginBottom: 2 },
  input: { backgroundColor: '#F4F5F7', color: Theme.ink, borderRadius: 14, padding: 12, minHeight: 110, textAlignVertical: 'top' },
  actions: { flexDirection: 'row', gap: 10, marginTop: 10 },
  btn: { backgroundColor: Theme.ink, borderRadius: 999, paddingVertical: 11, paddingHorizontal: 18 },
  btnText: { color: Theme.white, fontWeight: '800' },
  btnLight: { backgroundColor: '#F1F2F4' },
  btnLightText: { color: Theme.ink, fontWeight: '700' },
});
