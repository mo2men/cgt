import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
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