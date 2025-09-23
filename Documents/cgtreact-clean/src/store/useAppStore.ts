import { create } from 'zustand';
import { DisposalFragment, PoolSnapshot, CGTSummary } from '../types/models';

interface AppState {
    fragments: DisposalFragment[];
    snapshots: PoolSnapshot[];
    summaries: CGTSummary[];
    selectedYear: string;
    mode: 'strict' | 'reconciliation';
    setSelectedYear: (year: string) => void;
    setMode: (mode: 'strict' | 'reconciliation') => void;
  }
  
  export const useAppStore = create<AppState>((set) => ({
    fragments: [],
    snapshots: [],
    summaries: [],
    selectedYear: '2024-25',
    mode: 'strict',
    setSelectedYear: (year) => set({ selectedYear: year }),
    setMode: (mode) => set({ mode }),
  }));