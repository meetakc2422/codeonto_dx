import React from 'react';
import { RefreshControl, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import FilterBar from './FilterBar';
import { Theme } from '../constants/Colors';

/** Shared page frame: title and filters on top, scrolling content with pull-to-refresh, room for the floating tab bar. */
export default function Screen({ title, children, onRefresh, refreshing }: { title: string; children: React.ReactNode; onRefresh?: () => void; refreshing?: boolean }) {
  return (
    <SafeAreaView style={s.safe} edges={['top']}>
      <FilterBar title={title} />
      <ScrollView
        contentContainerStyle={s.content}
        refreshControl={onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={Theme.accent} /> : undefined}
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Theme.page },
  content: { padding: 18, paddingTop: 12, paddingBottom: 120 },
});
