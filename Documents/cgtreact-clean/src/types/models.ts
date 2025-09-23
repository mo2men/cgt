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
    tax_year_start: string;
    tax_year_end: string;
    cgt_allowance_gbp: number;
    allowance_used_gbp: number;
    taxable_income: number;
    basic_limit: number;
    basic_gain: number;
    higher_gain: number;
    effective_rate_percent: number;
    total_disposals: number;
    total_proceeds: number;
    total_cost: number;
    total_gain: number;
    net_gain: number;
    taxable_after_allowance: number;
    estimated_cgt: number;
  }