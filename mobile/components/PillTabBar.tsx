import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Theme } from '../constants/Colors';

/** A floating dark pill: icons for the tabs, and the active one opens into a lime pill with its name. */
// props come from expo-router's Tabs (a react-navigation bottom tab bar)
export default function PillTabBar({ state, descriptors, navigation }: any) {
  return (
    <SafeAreaView edges={['bottom']} style={s.wrap} pointerEvents="box-none">
      <View style={s.bar}>
        {state.routes.map((route: any, index: number) => {
          const { options } = descriptors[route.key];
          const active = state.index === index;
          const label = (options.title as string) || route.name;
          const icon = options.tabBarIcon?.({ focused: active, color: active ? Theme.ink : Theme.whiteMuted, size: 20 });
          return (
            <Pressable
              key={route.key}
              accessibilityLabel={label}
              onPress={() => { const e = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true }); if (!active && !e.defaultPrevented) navigation.navigate(route.name); }}
              style={[s.item, active && s.itemActive]}
            >
              {icon}
              {active ? <Text style={s.label}>{label}</Text> : null}
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  wrap: { position: 'absolute', left: 0, right: 0, bottom: 0, alignItems: 'center' },
  bar: { flexDirection: 'row', backgroundColor: '#17171B', borderRadius: 40, padding: 6, gap: 4, marginBottom: 8, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)' },
  item: { height: 46, minWidth: 46, borderRadius: 23, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 6, paddingHorizontal: 12, backgroundColor: '#26262C' },
  itemActive: { backgroundColor: Theme.lime, paddingHorizontal: 16 },
  label: { color: Theme.ink, fontWeight: '800', fontSize: 13 },
});
