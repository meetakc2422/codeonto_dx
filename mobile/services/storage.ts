import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

/** Small key-value storage: the phone's secure store in the app, the browser's localStorage on the web. */
const web = Platform.OS === 'web';

export const storage = {
  async get(key: string): Promise<string | null> {
    try { return web ? window.localStorage.getItem(key) : await SecureStore.getItemAsync(key); } catch { return null; }
  },
  async set(key: string, value: string): Promise<void> {
    try { if (web) window.localStorage.setItem(key, value); else await SecureStore.setItemAsync(key, value); } catch { /* storage can be blocked: the app still works for this visit */ }
  },
  async remove(key: string): Promise<void> {
    try { if (web) window.localStorage.removeItem(key); else await SecureStore.deleteItemAsync(key); } catch { /* nothing to remove */ }
  },
};
