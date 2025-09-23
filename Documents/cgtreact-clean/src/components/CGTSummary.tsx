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
        <Typography>Total Gain: £{summary.total_gain.toFixed(2)}</Typography>
        <Typography>AEA (Annual Exempt Amount): £{summary.allowance_used.toFixed(2)}</Typography>
        <Typography>Tax Due: £{summary.tax_due.toFixed(2)}</Typography>
      </CardContent>
    </Card>
  );
};

export default CGTSummary;