export interface BackendDisposalFragment {
  disposal_id: number;
  sale_date: string | null;
  sale_input_id: number;
  fragment_index: number;
  matched_shares: number;
  matching_type: string;
  lot_entry: string | null;
  matched_date: string | null;
  source: string | null;
  rate_used: string | null;
  avg_cost_gbp: number;
  proceeds_gbp: number;
  cost_basis_gbp: number;
  gain_gbp: number;
  pool_rsu_pct: number;
  pool_espp_pct: number;
  calculation_snippet: string[];
}

export interface DisposalFragment {
  id: number;
  sale_date: string;
  match_type: string;
  acquisition_cost: number;
  proceeds: number;
  gain: number;
  matched_shares: number;
  avg_cost_gbp: number;
  cost_basis_gbp: number;
  lot_entry?: string;
  matched_date?: string;
  source?: string;
  rate_used?: string;
  trace?: any;
}

export interface Vesting {
  id: number;
  date: string;
  shares_vested: number;
  price_usd?: number;
  total_usd?: number;
  exchange_rate?: number;
  total_gbp?: number;
  tax_paid_gbp?: number;
  incidental_costs_gbp?: number;
  shares_sold?: number;
  net_shares?: number;
}

export interface Espp {
  id: number;
  date: string;
  shares_retained: number;
  purchase_price_usd?: number;
  market_price_usd?: number;
  discount?: number;
  exchange_rate?: number;
  total_gbp?: number;
  discount_taxed_paye: boolean;
  paye_tax_gbp?: number;
  qualifying: boolean;
  incidental_costs_gbp?: number;
  notes?: string;
}

export interface Sale {
  id: number;
  date: string;
  shares_sold: number;
  sale_price_usd?: number;
  exchange_rate?: number;
  incidental_costs_gbp?: number;
}

export interface PoolSnapshot {
  timestamp: string;
  tax_year?: number;
  total_shares: number;
  total_cost_gbp: number;
  avg_cost_gbp: number;
  snapshot_json: string;
  lots: {
    source: string;
    quantity: number;
    cost: number;
  }[];
}

export interface BackendCGTSummary {
  tax_year_start: string;
  tax_year_end: string;
  cgt_allowance_gbp: number;
  carry_forward_loss_gbp: number;
  net_gain_after_losses: number;
  non_savings_income: number;
  basic_threshold: number;
  basic_band_available: number;
  total_disposals: number;
  total_proceeds: number;
  total_cost: number;
  total_gain: number;
  pos: number;
  neg: number;
  net_gain: number;
  taxable_after_allowance: number;
  basic_taxable_gain: number;
  higher_taxable_gain: number;
  estimated_cgt: number;
}

export interface CGTSummary {
  tax_year: string;
  tax_year_start: string;
  tax_year_end: string;
  cgt_allowance_gbp: number;
  carry_forward_loss_gbp: number;
  net_gain_after_losses: number;
  non_savings_income: number;
  basic_threshold: number;
  basic_band_available: number;
  total_disposals: number;
  total_proceeds: number;
  total_cost: number;
  total_gain: number;
  pos: number;
  neg: number;
  net_gain: number;
  taxable_after_allowance: number;
  basic_taxable_gain: number;
  higher_taxable_gain: number;
  estimated_cgt: number;
}

export interface SA108Export {
  tax_year: number;
  tax_year_start: string;
  tax_year_end: string;
  total_proceeds: number;
  total_costs: number;
  total_gains: number;
  total_losses: number;
  net_gain: number;
  allowable_loss: number;
  carry_forward_loss_used: number;
  net_gain_after_losses: number;
  cgt_allowance_used: number;
  chargeable_gain: number;
  disposals: Array<{
    date: string;
    description: string;
    proceeds: number;
    cost: number;
    gain_loss: number;
  }>;
}