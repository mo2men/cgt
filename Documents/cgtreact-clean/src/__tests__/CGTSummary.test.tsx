import React from 'react';
import { render, screen } from '@testing-library/react';
import { useAppStore } from '../store/useAppStore';
import CGTSummary from '../components/CGTSummary';

// Mock the store
jest.mock('../store/useAppStore');

const mockUseAppStore = useAppStore as jest.MockedFunction<typeof useAppStore>;

describe('CGTSummary', () => {
  const mockSummaries = [
    {
      tax_year: 2023,
      total_gain: 2000,
      carry_forward_loss_gbp: 500,
      net_gain_after_losses: 1500,
      cgt_allowance_gbp: 6000,
      allowance_used_gbp: 1500,
      taxable_income: 0,
      basic_gain: 0,
      higher_gain: 0,
      effective_rate_percent: 0,
      estimated_cgt: 0,
    },
  ];

  beforeEach(() => {
    mockUseAppStore.mockReturnValue({
      summaries: mockSummaries,
      selectedYear: 2023,
    });
  });

  it('renders summary for selected year', () => {
    render(<CGTSummary />);
    expect(screen.getByText('CGT Summary (2023)')).toBeInTheDocument();
    expect(screen.getByText('Total Gain: £2000.00')).toBeInTheDocument();
    expect(screen.getByText('AEA: £6000.00 (Used: £2000.00)')).toBeInTheDocument();
    expect(screen.getByText('Tax Due: £0.00')).toBeInTheDocument();
  });

  it('shows no summary message if no data for year', () => {
    mockUseAppStore.mockReturnValue({
      summaries: [],
      selectedYear: 2024,
    });
    render(<CGTSummary />);
    expect(screen.getByText('No CGT summary for 2024')).toBeInTheDocument();
  });
});