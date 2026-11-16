import React from 'react';
import { Tabs } from 'expo-router';
import { AlertTriangle, MessageSquareQuote, Power, WalletCards } from 'lucide-react-native';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#8B5CF6',
        tabBarInactiveTintColor: '#64748B',
        headerShown: false,
        tabBarStyle: { backgroundColor: '#0B0F17', borderTopColor: 'rgba(255,255,255,0.08)', borderTopWidth: 1, height: 64, paddingBottom: 8, paddingTop: 8 },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Stock-outs', tabBarIcon: ({ color }) => <AlertTriangle size={22} color={color} /> }} />
      <Tabs.Screen name="uptime" options={{ title: 'Uptime', tabBarIcon: ({ color }) => <Power size={22} color={color} /> }} />
      <Tabs.Screen name="reviews" options={{ title: 'Reviews', tabBarIcon: ({ color }) => <MessageSquareQuote size={22} color={color} /> }} />
      <Tabs.Screen name="payouts" options={{ title: 'Payouts', tabBarIcon: ({ color }) => <WalletCards size={22} color={color} /> }} />
    </Tabs>
  );
}
