import React, { useState } from 'react';
import { FlatList, Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { ChevronDown } from 'lucide-react-native';
import { useFilters } from '../context/FilterContext';
import { Colors } from '../constants/Colors';
import { Pill } from './ui';

const C = Colors.dark;

/** Brand, period and platform: the three choices every screen shares. */
export default function FilterBar() {
  const { brands, brand, setBrandId, days, setDays, platform, setPlatform } = useFilters();
  const [open, setOpen] = useState(false);
  return (
    <View style={s.wrap}>
      <Pressable style={s.brand} onPress={() => brands.length > 1 && setOpen(true)}>
        <Text style={s.brandText} numberOfLines={1}>{brand ? brand.name : 'Loading…'}</Text>
        {brands.length > 1 ? <ChevronDown size={16} color={C.textSecondary} /> : null}
      </Pressable>
      <View style={s.chips}>
        {[1, 7, 30, 90].map((d) => <Pill key={d} text={d === 1 ? 'Today' : `${d}D`} active={days === d} onPress={() => setDays(d)} />)}
        <View style={{ width: 8 }} />
        {([['', 'All'], ['zomato', 'Zomato'], ['swiggy', 'Swiggy']] as const).map(([v, l]) => (
          <Pill key={v} text={l} active={platform === v} onPress={() => setPlatform(v)} />
        ))}
      </View>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={s.backdrop} onPress={() => setOpen(false)}>
          <View style={s.sheet}>
            <Text style={s.sheetTitle}>Choose a brand</Text>
            <FlatList
              data={brands}
              keyExtractor={(b) => String(b.id)}
              renderItem={({ item }) => (
                <Pressable style={s.option} onPress={() => { setBrandId(item.id); setOpen(false); }}>
                  <Text style={[s.optionText, item.id === brand?.id && { color: Colors.primary }]}>{item.name}</Text>
                  <Text style={s.optionSub}>{item.client}</Text>
                </Pressable>
              )}
            />
          </View>
        </Pressable>
      </Modal>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 4 },
  brand: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  brandText: { color: C.text, fontSize: 22, fontWeight: '800', textTransform: 'capitalize', flexShrink: 1 },
  chips: { flexDirection: 'row', flexWrap: 'wrap' },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 16, maxHeight: '70%' },
  sheetTitle: { color: C.text, fontWeight: '700', fontSize: 16, marginBottom: 8 },
  option: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: C.cardBorder },
  optionText: { color: C.text, fontSize: 16, fontWeight: '600', textTransform: 'capitalize' },
  optionSub: { color: C.textMuted, fontSize: 12 },
});
