import { Stack, useRouter, useSegments } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { FilterProvider } from '../context/FilterContext';

export { ErrorBoundary } from 'expo-router';
export const unstable_settings = { initialRouteName: '(tabs)' };

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 1000 * 60 * 2 } } });

function Guard() {
  const { token, isLoading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    const onLogin = segments[0] === 'login';
    if (!token && !onLogin) router.replace('/login');
    else if (token && onLogin) router.replace('/(tabs)');
  }, [token, isLoading, segments]);

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="login" />
    </Stack>
  );
}

export default function RootLayout() {
  useEffect(() => { SplashScreen.hideAsync(); }, []);
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <FilterProvider>
          <StatusBar style="light" />
          <Guard />
        </FilterProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
