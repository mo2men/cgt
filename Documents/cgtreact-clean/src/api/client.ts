import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5002/api',
});

export const fetchFragments = async () => {
  const res = await api.get('/transactions');
  return res.data;
};

export const fetchSnapshot = async (year: string) => {
  const res = await api.get(`/snapshot/${year}`);
  return res.data;
};

export const fetchSummary = async (year: string) => {
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