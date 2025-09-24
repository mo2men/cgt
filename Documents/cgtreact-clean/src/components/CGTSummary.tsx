import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { Typography, Card, CardContent, Tooltip, Alert } from '@mui/material';

const CGTSummary = () => {
  const { summaries, selectedYear } = useAppStore();
  const summary = summaries.find(s => s.tax_year === selectedYear);

  if (!summary) return <Typography>No CGT summary for {selectedYear}</Typography>;

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Typography variant="h6">CGT Summary ({selectedYear})</Typography>
        <Tooltip title="Total gains from all disposals in the tax year. See HMRC HS284 for guidance on calculating gains.">
          <Typography>Total Gain: £{(summary.total_gain ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Losses carried forward from previous tax years, deducted from current year gains before AEA. Refer to TCGA 1992 s.2(2) and HMRC Capital Gains Manual.">
          <Typography>Carry Forward Loss: £{(summary.carry_forward_loss_gbp ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Net gain after deducting carry-forward losses.">
          <Typography>Net Gain after Losses: £{(summary.net_gain_after_losses ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Annual Exempt Amount (AEA) for the tax year. £3,000 for 2024/25, £6,000 for 2023/24. See HMRC: https://www.gov.uk/capital-gains-tax/allowances">
          <Typography>AEA: £{(summary.cgt_allowance_gbp ?? 0).toFixed(2)} (Used: £{(summary.allowance_used_gbp ?? 0).toFixed(2)})</Typography>
        </Tooltip>
        <Tooltip title="Non-savings taxable income affects the basic rate band for CGT. Enter in Settings. Assumptions: basic/higher rate taxpayer.">
          <Typography>Taxable Income: £{(summary.taxable_income ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Gains taxed at 10% within the basic rate band (£37,700 minus taxable income). See HMRC: https://www.gov.uk/capital-gains-tax/rates">
          <Typography>Basic Gain: £{(summary.basic_gain ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Gains taxed at 20% above the basic rate band.">
          <Typography>Higher Gain: £{(summary.higher_gain ?? 0).toFixed(2)}</Typography>
        </Tooltip>
        <Tooltip title="Overall effective CGT rate after all calculations.">
          <Typography>Effective Rate: {(summary.effective_rate_percent ?? 0).toFixed(2)}%</Typography>
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
      </CardContent>
    </Card>
  );
};

export default CGTSummary;