import React from 'react';
import { Tabs } from 'expo-router';
import { AlertTriangle, MessageSquareText, Power, TrendingUp, WalletCards } from 'lucide-react-native';
import PillTabBar from '../../components/PillTabBar';

export default function TabLayout() {
  return (
    <Tabs tabBar={(props: any) => <PillTabBar {...props} />} screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="index" options={{ title: 'Insights', tabBarIcon: ({ color }) => <TrendingUp size={20} color={color} /> }} />
      <Tabs.Screen name="reviews" options={{ title: 'Reviews', tabBarIcon: ({ color }) => <MessageSquareText size={20} color={color} /> }} />
      <Tabs.Screen name="stockouts" options={{ title: 'Stock-outs', tabBarIcon: ({ color }) => <AlertTriangle size={20} color={color} /> }} />
      <Tabs.Screen name="uptime" options={{ title: 'Uptime', tabBarIcon: ({ color }) => <Power size={20} color={color} /> }} />
      <Tabs.Screen name="payouts" options={{ title: 'Payouts', tabBarIcon: ({ color }) => <WalletCards size={20} color={color} /> }} />
    </Tabs>
  );
}
