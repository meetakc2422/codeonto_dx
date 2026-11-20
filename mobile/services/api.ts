import axios from 'axios';
import { storage } from './storage';

// The Compass dashboard API (the same one the website uses). Set EXPO_PUBLIC_API_URL to point at another server,
// e.g. http://192.168.1.x:8000/api for a Django server on your Mac while developing.
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://compass.codeonto.com/api';

const TOKEN_KEY = 'co_token';
const USER_KEY = 'co_user';

export const apiClient = axios.create({ baseURL: API_BASE_URL, timeout: 25000 });

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

apiClient.interceptors.request.use(async (config) => {
  const token = await storage.get(TOKEN_KEY);
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
  saveToken: (t: string) => storage.set(TOKEN_KEY, t),
  getToken: () => storage.get(TOKEN_KEY),
  saveUser: (u: unknown) => storage.set(USER_KEY, JSON.stringify(u)),
  async getUser() {
    const raw = await storage.get(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },
  async clear() {
    await storage.remove(TOKEN_KEY);
    await storage.remove(USER_KEY);
  },
};

// What a person may read when a request fails: a sentence the server wrote for people, else a plain one.
// Status codes, "Request failed with status code 500" and exception text stay out of the screen.
export function errorText(e: any): string {
  const detail = e?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (!e?.response) return "We couldn't reach Compass. Check your internet connection and try again.";
  const status = e.response.status;
  if (status === 403) return "You don't have access to this.";
  if (status === 404) return "We couldn't find that.";
  if (status === 429) return 'Too many requests. Please wait a moment and try again.';
  if (status >= 500) return 'Something went wrong on our side. Please try again in a moment.';
  return "That didn't work. Please try again.";
}
