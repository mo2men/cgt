import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5002/api',
});

export const fetchFragments = async (year: string) => {
  const res = await api.get('/transactions');
  const yearNum = parseInt(year.split('-')[0]);
  const filteredData = res.data.items.filter((item: any) => {
    const saleYear = parseInt(item.sale_date.split('-')[0]);
    return saleYear === yearNum;
  });
  return filteredData;
};

export const fetchSnapshot = async (year: number) => {
  const res = await api.get(`/snapshot/${year}`);
  return res.data;
};

export const fetchSummary = async (year: number) => {
  const res = await api.get(`/summary/${year}`);
  return res.data;
};

export const updateSettings = async (key: string, value: any) => {
  const res = await api.post('/settings', { key, value });
  return res.data;
};

// Vesting CRUD
export const createVesting = async (vestingData: any) => {
  const res = await api.post('/vestings', vestingData);
  return res.data;
};

export const getVestings = async () => {
  const res = await api.get('/vestings');
  return res.data;
};

export const updateVesting = async (id: number, vestingData: any) => {
  const res = await api.put(`/vestings/${id}`, vestingData);
  return res.data;
};

export const deleteVesting = async (id: number) => {
  const res = await api.delete(`/vestings/${id}`);
  return res.data;
};

// ESPP CRUD
export const createEspp = async (esppData: any) => {
  const res = await api.post('/espp', esppData);
  return res.data;
};

export const getEspp = async () => {
  const res = await api.get('/espp');
  return res.data;
};

export const updateEspp = async (id: number, esppData: any) => {
  const res = await api.put(`/espp/${id}`, esppData);
  return res.data;
};

export const deleteEspp = async (id: number) => {
  const res = await api.delete(`/espp/${id}`);
  return res.data;
};

// Sales CRUD
export const createSale = async (saleData: any) => {
  const res = await api.post('/sales', saleData);
  return res.data;
};

export const getSales = async () => {
  const res = await api.get('/sales');
  return res.data;
};

export const updateSale = async (id: number, saleData: any) => {
  const res = await api.put(`/sales/${id}`, saleData);
  return res.data;
};

export const deleteSale = async (id: number) => {
  const res = await api.delete(`/sales/${id}`);
  return res.data;
};
export const fetchTransaction = async (id: number) => {
  const res = await api.get(`/transaction/${id}`);
  return res.data;
};

export const fetchSa108Export = async (year: number) => {
  const res = await api.get(`/export/sa108/${year}`);
  return res.data;
};

// Stock API
export const getStockCurrent = async (ticker: string) => {
  const res = await api.get(`/stock/current?ticker=${ticker}`);
  return res.data;
};

export const getStockHistory = async (ticker: string, days: number = 100) => {
  const res = await api.get(`/stock/history?ticker=${ticker}&days=${days}`);
  return res.data;
};

export const getStockPredict = async (ticker: string, options: { method: string; horizon: number }) => {
  const params = new URLSearchParams({
    ticker,
    method: options.method,
    horizon: options.horizon.toString()
  });
  const res = await api.get(`/stock/predict?${params.toString()}`);
  return res.data;
};

export const getStockOptimize = async (ticker: string, options: { horizon: number; fraction: number }) => {
  const params = new URLSearchParams({
    ticker,
    horizon: options.horizon.toString(),
    fraction: options.fraction.toString()
  });
  const res = await api.get(`/stock/optimize?${params.toString()}`);
  return res.data;
};

// Audit logs
export const recalc = async (taxYear: string) => {
  const res = await api.post('/recalc', { tax_year: taxYear });
  return res.data;
};

export const fetchCalculationSteps = async (taxYear?: number, saleId?: number) => {
  const params = new URLSearchParams();
  if (taxYear) params.set('tax_year', taxYear.toString());
  if (saleId) params.set('sale_id', saleId.toString());
  const res = await api.get(`/calculation-steps?${params.toString()}`);
  return res.data.steps;
};