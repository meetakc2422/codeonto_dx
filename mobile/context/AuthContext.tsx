import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { apiClient, authStorage, setUnauthorizedHandler } from '../services/api';

type User = { username: string; name: string; email: string; is_staff: boolean; client: { id: number; name: string } | null; can_edit: boolean };
type AuthState = {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState>({} as AuthState);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setLoading] = useState(true);

  const logout = useCallback(async () => {
    await authStorage.clear();
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null);
      setUser(null);
    });
    (async () => {
      const [t, u] = await Promise.all([authStorage.getToken().catch(() => null), authStorage.getUser().catch(() => null)]);
      setToken(t);
      setUser(u);
      setLoading(false);
    })();
    return () => setUnauthorizedHandler(null);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { data } = await apiClient.post('/auth/mobile/login', { username: username.trim(), password });
    await authStorage.saveToken(data.token);
    await authStorage.saveUser(data.user);
    setToken(data.token);
    setUser(data.user);
  }, []);

  return <AuthContext.Provider value={{ token, user, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}
