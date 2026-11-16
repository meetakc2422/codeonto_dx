import React, { useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Screen from '../../components/Screen';
import { Card, Empty, ErrorBox, Loading, Pill, Row, SectionTitle, Stat, ago } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import { useFilters } from '../../context/FilterContext';
import { apiClient, errorText } from '../../services/api';
import { Colors } from '../../constants/Colors';

const C = Colors.dark;
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
  const star = r.rating == null ? '—' : `${r.rating}★`;
  return (
    <Card>
      <Pressable onPress={() => { setOpen(!open); if (!open && !text) setText(suggest(r, brandName)); }}>
        <View style={s.top}>
          <Text style={[s.stars, { color: r.rating != null && r.rating <= 2 ? Colors.danger : r.rating === 3 ? Colors.warning : Colors.success }]}>{star}</Text>
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
          <TextInput style={s.input} multiline value={text} onChangeText={setText} placeholder="Write a reply…" placeholderTextColor={C.textMuted} />
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

export default function Reviews() {
  const { brand, params } = useFilters();
  const { user } = useAuth();
  const id = brand?.id;
  const [filter, setFilter] = useState<Filter>('pending');
  const summary = useQuery({
    queryKey: ['reviews-summary', id, params],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/reviews/summary`, { params })).data,
  });
  const list = useQuery({
    queryKey: ['reviews', id, params, filter],
    enabled: !!id,
    queryFn: async () => (await apiClient.get(`/brands/${id}/reviews`, {
      params: { ...params, limit: 40, ...(filter === 'pending' ? { reply_status: 'pending' } : {}), ...(filter === 'neg' ? { rating: 'neg' } : {}) },
    })).data as any[],
  });
  const d = summary.data;
  const refetch = () => { summary.refetch(); list.refetch(); };

  return (
    <Screen onRefresh={refetch} refreshing={list.isRefetching}>
      {summary.isLoading ? <Loading /> : summary.error ? <ErrorBox text={errorText(summary.error)} onRetry={refetch} /> : d ? (
        <>
          <Row>
            <Stat label="Avg rating" value={d.avg_rating ? `${d.avg_rating.toFixed(2)}★` : '—'} tone={d.avg_rating && d.avg_rating < 4 ? 'warn' : 'ok'} />
            <Stat label="Reviews" value={String(d.total)} sub={`${d.replied} replied`} />
          </Row>
          <Row>
            <Stat label="To reply" value={String(d.pending)} tone={d.pending ? 'warn' : 'ok'} />
            <Stat label="1–2★" value={String(d.negative)} tone={d.negative ? 'bad' : 'ok'} />
          </Row>
          <SectionTitle title="What customers talk about" hint="reviews mentioning each topic · 1–2★ in red" />
          <View style={s.chips}>
            {(d.by_topic?.topics || []).filter((t: any) => t.count).sort((a: any, b: any) => b.count - a.count).slice(0, 8).map((t: any) => (
              <Pill key={t.slug} tone={t.negative ? 'red' : 'grey'} text={`${t.label} ${t.count}${t.negative ? ` · ${t.negative}` : ''}`} />
            ))}
          </View>
        </>
      ) : null}

      <SectionTitle title="Reviews" />
      <View style={s.chips}>
        {([['pending', 'To reply'], ['neg', '1–2★'], ['', 'All']] as [Filter, string][]).map(([v, l]) => <Pill key={v || 'all'} text={l} active={filter === v} onPress={() => setFilter(v)} />)}
      </View>
      {list.isLoading ? <Loading /> : list.error ? <ErrorBox text={errorText(list.error)} onRetry={refetch} /> :
        (list.data || []).length === 0 ? <Empty text="No reviews here." /> :
        (list.data || []).map((r) => <ReviewCard key={r.id} r={r} brandName={brand?.name?.replace(/\b\w/g, (c) => c.toUpperCase()) || ''} canEdit={user?.can_edit !== false} />)}
    </Screen>
  );
}

const s = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 8 },
  top: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  stars: { fontSize: 15, fontWeight: '800' },
  meta: { color: C.textMuted, fontSize: 12, flex: 1 },
  body: { color: C.text, fontSize: 14, lineHeight: 20 },
  author: { color: C.textMuted, fontSize: 12, marginTop: 6 },
  reply: { marginTop: 10, borderLeftWidth: 3, borderLeftColor: Colors.primary, paddingLeft: 10 },
  replyText: { color: C.textSecondary, fontSize: 13, lineHeight: 18 },
  hint: { color: C.textMuted, fontSize: 12, marginBottom: 6 },
  input: { backgroundColor: C.surface, color: C.text, borderRadius: 10, padding: 10, minHeight: 110, textAlignVertical: 'top', borderWidth: 1, borderColor: C.cardBorder },
  actions: { flexDirection: 'row', gap: 10, marginTop: 10 },
  btn: { backgroundColor: Colors.primary, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 16 },
  btnText: { color: '#fff', fontWeight: '700' },
  btnLight: { backgroundColor: '#1f2937' },
  btnLightText: { color: C.text, fontWeight: '600' },
});
