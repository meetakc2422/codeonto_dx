import React, { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { ChevronDown, SlidersHorizontal } from 'lucide-react-native';
import { useFilters } from '../context/FilterContext';
import { useAuth } from '../context/AuthContext';
import { Theme } from '../constants/Colors';

type Option = { value: string; label: string; sub?: string };

function Sheet({ title, options, value, onPick, onClose }: { title: string; options: Option[]; value: string; onPick: (v: string) => void; onClose: () => void }) {
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={s.backdrop} onPress={onClose}>
        <View style={s.sheet}>
          <Text style={s.sheetTitle}>{title}</Text>
          {options.map((o) => (
            <Pressable key={o.value} style={s.option} onPress={() => { onPick(o.value); onClose(); }}>
              <Text style={[s.optionText, o.value === value && { color: Theme.ink, fontWeight: '800' }]}>{o.label}</Text>
              {o.value === value ? <View style={s.dot} /> : o.sub ? <Text style={s.optionSub}>{o.sub}</Text> : null}
            </Pressable>
          ))}
        </View>
      </Pressable>
    </Modal>
  );
}

/** Page title with the account circle, then three chips: brand, period, and Filters (platform). Every tab shares it. */
export default function FilterBar({ title }: { title: string }) {
  const { brands, brand, setBrandId, days, setDays, platform, setPlatform } = useFilters();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState<'' | 'brand' | 'period' | 'filters' | 'me'>('');
  const periodLabel = days === 1 ? 'Today' : `Last ${days} Days`;
  const initial = (user?.name || user?.username || 'S').trim().charAt(0).toUpperCase();

  return (
    <View style={s.wrap}>
      <View style={s.titleRow}>
        <Text style={s.title}>{title}</Text>
        <Pressable style={s.avatar} onPress={() => setOpen('me')}><Text style={s.avatarText}>{initial}</Text></Pressable>
      </View>
      <View style={s.chips}>
        <Pressable style={s.chip} onPress={() => brands.length > 1 && setOpen('brand')}>
          <Text style={s.chipText} numberOfLines={1}>{brand ? brand.name : 'Loading…'}</Text>
          {brands.length > 1 ? <ChevronDown size={14} color={Theme.ink} /> : null}
        </Pressable>
        <Pressable style={s.chip} onPress={() => setOpen('period')}>
          <Text style={s.chipText}>{periodLabel}</Text>
          <ChevronDown size={14} color={Theme.ink} />
        </Pressable>
        <Pressable style={[s.chip, { backgroundColor: platform ? Theme.lime : '#FBE3E3' }]} onPress={() => setOpen('filters')}>
          <Text style={s.chipText}>{platform ? (platform === 'zomato' ? 'Zomato' : 'Swiggy') : 'Filters'}</Text>
          <SlidersHorizontal size={14} color={Theme.ink} />
        </Pressable>
      </View>

      {open === 'brand' ? <Sheet title="Choose a brand" value={String(brand?.id)} options={brands.map((b) => ({ value: String(b.id), label: b.name, sub: b.client }))} onPick={(v) => setBrandId(Number(v))} onClose={() => setOpen('')} /> : null}
      {open === 'period' ? <Sheet title="Period" value={String(days)} options={[{ value: '1', label: 'Today' }, { value: '7', label: 'Last 7 Days' }, { value: '30', label: 'Last 30 Days' }, { value: '90', label: 'Last 90 Days' }]} onPick={(v) => setDays(Number(v))} onClose={() => setOpen('')} /> : null}
      {open === 'filters' ? <Sheet title="Platform" value={platform} options={[{ value: '', label: 'All platforms' }, { value: 'zomato', label: 'Zomato' }, { value: 'swiggy', label: 'Swiggy' }]} onPick={(v) => setPlatform(v as '' | 'zomato' | 'swiggy')} onClose={() => setOpen('')} /> : null}
      {open === 'me' ? <Sheet title={`Signed in as ${user?.username || ''}`} value="" options={[{ value: 'out', label: 'Sign out' }]} onPick={() => logout()} onClose={() => setOpen('')} /> : null}
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { paddingHorizontal: 18, paddingTop: 6, paddingBottom: 6 },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  title: { color: Theme.white, fontSize: 32, fontWeight: '700' },
  avatar: { width: 38, height: 38, borderRadius: 19, backgroundColor: Theme.lime, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: Theme.ink, fontWeight: '800' },
  chips: { flexDirection: 'row', gap: 8 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: Theme.white, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 9, maxWidth: '45%' },
  chipText: { color: Theme.ink, fontWeight: '700', fontSize: 13, textTransform: 'capitalize', flexShrink: 1 },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.65)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: Theme.paper, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 20, paddingBottom: 36, maxHeight: '75%' },
  sheetTitle: { color: Theme.ink, fontWeight: '800', fontSize: 18, marginBottom: 8 },
  option: { paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: Theme.line, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  optionText: { color: Theme.inkMuted, fontSize: 16, textTransform: 'capitalize' },
  optionSub: { color: Theme.inkMuted, fontSize: 12 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: Theme.lime, borderWidth: 1, borderColor: Theme.ink },
});
