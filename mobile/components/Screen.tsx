import React from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import FilterBar from './FilterBar';
import { Colors } from '../constants/Colors';

/** Shared page frame: filters on top, scrolling content with pull-to-refresh. */
export default function Screen({ children, onRefresh, refreshing }: { children: React.ReactNode; onRefresh?: () => void; refreshing?: boolean }) {
  return (
    <SafeAreaView style={s.safe} edges={['top']}>
      <FilterBar />
      <ScrollView
        contentContainerStyle={s.content}
        refreshControl={onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={Colors.primary} /> : undefined}
      >
        <View>{children}</View>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.dark.background },
  content: { padding: 16, paddingBottom: 40 },
});
