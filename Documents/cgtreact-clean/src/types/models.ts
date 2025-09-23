export interface DisposalFragment {
    id: string;
    sale_date: string;
    match_type: string;
    acquisition_cost: number;
    proceeds: number;
    gain: number;
    trace: any;
  }
  
  export interface PoolSnapshot {
    tax_year: string;
    lots: {
      source: string;
      quantity: number;
      cost: number;
    }[];
  }
  
  export interface CGTSummary {
    tax_year: string;
    total_gain: number;
    allowance_used: number;
    tax_due: number;
  }