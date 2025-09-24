import { create } from 'zustand';
import { DisposalFragment, PoolSnapshot, CGTSummary } from '../types/models';

interface AppState {
    fragments: DisposalFragment[];
    snapshots: PoolSnapshot[];
    summaries: CGTSummary[];
    selectedYear: string;
    mode: 'strict' | 'reconciliation';
    selectedFragment: DisposalFragment | null;
    setSelectedYear: (year: string) => void;
    setMode: (mode: 'strict' | 'reconciliation') => void;
    setSelectedFragment: (fragment: DisposalFragment | null) => void;
  }
  
  export const useAppStore = create<AppState>((set) => ({
    fragments: [],
    snapshots: [],
    summaries: [],
    selectedYear: '2024-25',
    mode: 'strict',
    selectedFragment: null,
    setSelectedYear: (year) => set({ selectedYear: year }),
    setMode: (mode) => set({ mode }),
    setSelectedFragment: (fragment) => set({ selectedFragment: fragment }),
  }));