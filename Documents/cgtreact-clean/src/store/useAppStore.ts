import { create } from 'zustand';
import { DisposalFragment, PoolSnapshot, CGTSummary, StockHistory, Prediction, OptimizeResult, CalculationStep } from '../types/models';

interface AppState {
    fragments: DisposalFragment[];
    snapshots: PoolSnapshot[];
    summaries: CGTSummary[];
    auditSteps: CalculationStep[];
    selectedYear: string;
    mode: 'strict' | 'reconciliation';
    selectedFragment: DisposalFragment | null;
    // Stock state
    ticker: string;
    currentPrice: { price_gbp: number; price_usd: number; volume?: number } | null;
    history: StockHistory[];
    predictions: Prediction[];
    optimizeResult: OptimizeResult | null;
    setSelectedYear: (year: string) => void;
    setMode: (mode: 'strict' | 'reconciliation') => void;
    setSelectedFragment: (fragment: DisposalFragment | null) => void;
    setAuditSteps: (steps: CalculationStep[]) => void;
    // Stock setters
    setTicker: (ticker: string) => void;
    setCurrentPrice: (price: { price_gbp: number; price_usd: number; volume?: number } | null) => void;
    setHistory: (history: StockHistory[]) => void;
    setPredictions: (predictions: Prediction[]) => void;
    setOptimizeResult: (result: OptimizeResult | null) => void;
  }
  
  export const useAppStore = create<AppState>((set) => ({
    fragments: [],
    snapshots: [],
    summaries: [],
    auditSteps: [],
    selectedYear: '2024-25',
    mode: 'strict',
    selectedFragment: null,
    // Stock state
    ticker: '',
    currentPrice: null,
    history: [],
    predictions: [],
    optimizeResult: null,
    setSelectedYear: (year) => set({ selectedYear: year }),
    setMode: (mode) => set({ mode }),
    setSelectedFragment: (fragment) => set({ selectedFragment: fragment }),
    setAuditSteps: (auditSteps) => set({ auditSteps }),
    // Stock setters
    setTicker: (ticker) => set({ ticker }),
    setCurrentPrice: (currentPrice) => set({ currentPrice }),
    setHistory: (history) => set({ history }),
    setPredictions: (predictions) => set({ predictions }),
    setOptimizeResult: (optimizeResult) => set({ optimizeResult }),
  }));