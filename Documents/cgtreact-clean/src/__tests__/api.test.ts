import { fetchFragments, fetchSnapshot, fetchSummary } from '../api/client';
import axios from 'axios';

// Mock axios
jest.mock('axios');

const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches fragments successfully', async () => {
    const mockData = { items: [{ id: '1', sale_date: '2023-01-01' }] };
    mockedAxios.get.mockResolvedValueOnce({ data: mockData });

    const result = await fetchFragments();
    expect(mockedAxios.get).toHaveBeenCalledWith('/transactions');
    expect(result).toEqual(mockData);
  });

  it('fetches snapshot for year', async () => {
    const year = '2023';
    const mockData = { tax_year: 2023, total_shares: 1000 };
    mockedAxios.get.mockResolvedValueOnce({ data: mockData });

    const result = await fetchSnapshot(year);
    expect(mockedAxios.get).toHaveBeenCalledWith(`/snapshot/${year}`);
    expect(result).toEqual(mockData);
  });

  it('fetches summary for year matching CGTSummary interface', async () => {
    const year = '2023';
    const mockData = {
      tax_year_start: '2023-04-06',
      tax_year_end: '2024-04-05',
      cgt_allowance_gbp: 6000,
      allowance_used_gbp: 0,
      taxable_income: 0,
      basic_gain: 0,
      higher_gain: 0,
      effective_rate_percent: 0,
      total_disposals: 1,
      total_proceeds: 10000,
      total_cost: 5000,
      total_gain: 5000,
      net_gain: 5000,
      taxable_after_allowance: 0,
      estimated_cgt: 0,
    };
    mockedAxios.get.mockResolvedValueOnce({ data: mockData });

    const result = await fetchSummary(year);
    expect(mockedAxios.get).toHaveBeenCalledWith(`/summary/${year}`);
    expect(result).toEqual(mockData);
    // Verify structure matches CGTSummary
    expect(result.tax_year_start).toBeDefined();
    expect(result.estimated_cgt).toBeDefined();
  });

  it('handles API errors', async () => {
    const error = new Error('Network error');
    mockedAxios.get.mockRejectedValueOnce(error);

    await expect(fetchSummary('2023')).rejects.toThrow('Network error');
  });
});