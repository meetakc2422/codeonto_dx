import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// The SocialSpork dashboard API (the same one the website uses). Set EXPO_PUBLIC_API_URL to point at another server,
// e.g. http://192.168.1.x:8000/api for a Django server on your Mac while developing.
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://app.socialspork.com/api';

const TOKEN_KEY = 'ss_token';
const USER_KEY = 'ss_user';

export const apiClient = axios.create({ baseURL: API_BASE_URL, timeout: 25000 });

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

apiClient.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync(TOKEN_KEY).catch(() => null);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (r) => r,
  async (error) => {
    // a rejected token (expired, password changed): forget it and send the person back to the sign-in screen
    if (error.response?.status === 401 && !String(error.config?.url || '').includes('/auth/mobile/login')) {
      await authStorage.clear();
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);

export const authStorage = {
  saveToken: (t: string) => SecureStore.setItemAsync(TOKEN_KEY, t),
  getToken: () => SecureStore.getItemAsync(TOKEN_KEY),
  saveUser: (u: unknown) => SecureStore.setItemAsync(USER_KEY, JSON.stringify(u)),
  async getUser() {
    const raw = await SecureStore.getItemAsync(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },
  async clear() {
    await SecureStore.deleteItemAsync(TOKEN_KEY).catch(() => {});
    await SecureStore.deleteItemAsync(USER_KEY).catch(() => {});
  },
};

export function errorText(e: any): string {
  return e?.response?.data?.detail || e?.message || 'Something went wrong';
}
