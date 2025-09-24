import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { Typography, Card, CardContent, Tooltip, Alert, Button } from '@mui/material';
import { fetchSa108Export } from '../api/client';
import { SA108Export } from '../types/models';

const CGTSummary = () => {
  const { summaries, selectedYear } = useAppStore();
  const summary = summaries.find(s => s.tax_year === selectedYear);

  if (!summary) return <Typography>No CGT summary for {selectedYear}</Typography>;

  const handleSa108Download = async () => {
    try {
      const year = parseInt(selectedYear.split('-')[0]);
      const data: SA108Export = await fetchSa108Export(year);
      const csvContent = [
        ['Tax Year', `${data.tax_year_start} to ${data.tax_year_end}`],
        ['Total Proceeds', `£${data.total_proceeds.toFixed(2)}`],
        ['Total Costs', `£${data.total_costs.toFixed(2)}`],
        ['Total Gains', `£${data.total_gains.toFixed(2)}`],
        ['Total Losses', `£${data.total_losses.toFixed(2)}`],
        ['Net Gain', `£${data.net_gain.toFixed(2)}`],
        ['Allowable Loss', `£${data.allowable_loss.toFixed(2)}`],
        ['Carry Forward Loss Used', `£${data.carry_forward_loss_used.toFixed(2)}`],
        ['Net Gain After Losses', `£${data.net_gain_after_losses.toFixed(2)}`],
        ['CGT Allowance Used', `£${data.cgt_allowance_used.toFixed(2)}`],
        ['Chargeable Gain', `£${data.chargeable_gain.toFixed(2)}`],
        [''],
        ['Disposals Details'],
        ['Date', 'Description', 'Proceeds', 'Cost', 'Gain/Loss'],
        ...data.disposals.map(d => [d.date, d.description, `£${d.proceeds.toFixed(2)}`, `£${d.cost.toFixed(2)}`, `£${d.gain_loss.toFixed(2)}`])
      ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `SA108_${data.tax_year}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error downloading SA108:', error);
      alert('Failed to download SA108 export. Please try again.');
    }
  };

  const allowanceUsed = Math.min(summary.net_gain_after_losses ?? 0, summary.cgt_allowance_gbp ?? 0);
  const effectiveRate = (summary.net_gain_after_losses ?? 0) > 0 ? ((summary.estimated_cgt ?? 0) / (summary.net_gain_after_losses ?? 0) * 100) : 0;

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Typography variant="h6">CGT Summary ({selectedYear})</Typography>
        <Tooltip title="Total gains from all disposals in the tax year. See HMRC HS284 for guidance on calculating gains.">
          <Typography>Total Gain: £{(summary.total_gain ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Total losses in the current tax year, offset against gains before carry-forward losses. Excess carried forward to future years per TCGA 1992 s.2(2).">
          <Typography>Current Losses: £{(summary.neg ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Losses carried forward from previous tax years, deducted from current year gains before AEA. Refer to TCGA 1992 s.2(2) and HMRC Capital Gains Manual.">
          <Typography>Carry Forward Loss: £{(summary.carry_forward_loss_gbp ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Net gain after deducting carry-forward losses.">
          <Typography>Net Gain after Losses: £{(summary.net_gain_after_losses ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Annual Exempt Amount (AEA) for the tax year. £3,000 for 2024/25, £6,000 for 2023/24. See HMRC: https://www.gov.uk/capital-gains-tax/allowances">
          <Typography>AEA: £{(summary.cgt_allowance_gbp ?? 0).toFixed(2)} (Used: £{allowanceUsed.toFixed(2)})</Typography>
        </Tooltip>
        <Tooltip title="Non-savings taxable income affects the basic rate band for CGT. Enter in Settings. Assumptions: basic/higher rate taxpayer.">
          <Typography>Taxable Income: £{(summary.non_savings_income ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Gains taxed at 10% within the basic rate band (£37,700 minus taxable income). See HMRC: https://www.gov.uk/capital-gains-tax/rates">
          <Typography>Basic Gain: £{(summary.basic_taxable_gain ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Gains taxed at 20% above the basic rate band.">
          <Typography>Higher Gain: £{(summary.higher_taxable_gain ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Overall effective CGT rate after all calculations.">
          <Typography>Effective Rate: {effectiveRate.toFixed(2)}%</Typography>
        </Tooltip>
        <Tooltip title="Estimated CGT liability. This is an estimate - consult a tax advisor for your specific circumstances. Assumptions made may not apply to all cases (e.g., additional rate taxpayers, residential property).">
          <Typography>Tax Due: £{(summary.estimated_cgt ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="caption">
            <strong>Important Disclaimers:</strong><br />
            - <strong>ESPP:</strong> Assumes qualifying plans (discount ≤15%, hold 5 years or 90% FMV). For non-qualifying, full market value at exercise is income-taxed; ensure PAYE relief is correctly flagged. See HMRC ERSM.<br />
            - <strong>Residency:</strong> Assumes full-year UK resident; no split-year treatment (TCGA s.10A) or remittance basis (s.12).<br />
            - <strong>Reliefs:</strong> Does not include VCT/EIS (s.150), holdover (s.165), or business asset disposal relief (£1m lifetime, FA 2020).<br />
            - This tool is for guidance only; consult a qualified tax advisor for personalized advice.
          </Typography>
        </Alert>
        <Button
          variant="outlined"
          onClick={handleSa108Download}
          sx={{ mt: 2 }}
          size="small"
        >
          Download SA108 Export (CSV)
        </Button>
      </CardContent>
    </Card>
  );
};

export default CGTSummary;