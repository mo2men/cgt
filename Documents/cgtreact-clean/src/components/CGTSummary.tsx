import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { Typography, Card, CardContent } from '@mui/material';

const CGTSummary = () => {
  const { summaries, selectedYear } = useAppStore();
  const summary = summaries.find(s => s.tax_year === selectedYear);

  if (!summary) return <Typography>No CGT summary for {selectedYear}</Typography>;

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Typography variant="h6">CGT Summary ({selectedYear})</Typography>
        <Typography>Total Gain: £{(summary.total_gain ?? 0).toFixed(2)}</Typography>
        <Typography>AEA: £{(summary.cgt_allowance_gbp ?? 0).toFixed(2)} (Used: £{(summary.allowance_used_gbp ?? 0).toFixed(2)})</Typography>
        <Typography>Taxable Income: £{(summary.taxable_income ?? 0).toFixed(2)}</Typography>
        <Typography>Basic Gain: £{(summary.basic_gain ?? 0).toFixed(2)}</Typography>
        <Typography>Higher Gain: £{(summary.higher_gain ?? 0).toFixed(2)}</Typography>
        <Typography>Effective Rate: {(summary.effective_rate_percent ?? 0).toFixed(2)}%</Typography>
        <Typography>Tax Due: £{(summary.estimated_cgt ?? 0).toFixed(2)}</Typography>
      </CardContent>
    </Card>
  );
};

export default CGTSummary;