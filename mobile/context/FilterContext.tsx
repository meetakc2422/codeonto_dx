import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { storage } from '../services/storage';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { useAuth } from './AuthContext';

export type Brand = { id: number; name: string; client: string };
type Filters = {
  brands: Brand[];
  brand: Brand | null;
  setBrandId: (id: number) => void;
  days: number;
  setDays: (d: number) => void;
  platform: '' | 'zomato' | 'swiggy';
  setPlatform: (p: '' | 'zomato' | 'swiggy') => void;
  params: { start: string; end: string; platform?: string };
  loadingBrands: boolean;
};

const Ctx = createContext<Filters>({} as Filters);
export const useFilters = () => useContext(Ctx);

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export function FilterProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const [brandId, setBrandIdState] = useState<number | null>(null);
  const [days, setDaysState] = useState(7);
  const [platform, setPlatformState] = useState<'' | 'zomato' | 'swiggy'>('');

  const { data: brands = [], isLoading } = useQuery<Brand[]>({
    queryKey: ['brands', !!token],
    queryFn: async () => (await apiClient.get('/brands')).data,
    enabled: !!token,
  });

  useEffect(() => {
    storage.get('ss_filters')
      .then((raw) => {
        if (!raw) return;
        const f = JSON.parse(raw);
        if (f.brandId) setBrandIdState(f.brandId);
        if (f.days) setDaysState(f.days);
        if (f.platform !== undefined) setPlatformState(f.platform);
      })
      .catch(() => {});
  }, []);

  const save = (next: { brandId: number | null; days: number; platform: string }) =>
    storage.set('ss_filters', JSON.stringify(next));

  const brand = useMemo(() => brands.find((b) => b.id === brandId) || brands[0] || null, [brands, brandId]);

  const value = useMemo<Filters>(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - (days - 1));
    return {
      brands,
      brand,
      setBrandId: (id) => { setBrandIdState(id); save({ brandId: id, days, platform }); },
      days,
      setDays: (d) => { setDaysState(d); save({ brandId: brand?.id ?? null, days: d, platform }); },
      platform,
      setPlatform: (p) => { setPlatformState(p); save({ brandId: brand?.id ?? null, days, platform: p }); },
      params: { start: iso(start), end: iso(end), ...(platform ? { platform } : {}) },
      loadingBrands: isLoading,
    };
  }, [brands, brand, days, platform, isLoading]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
