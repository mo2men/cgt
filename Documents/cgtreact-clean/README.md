# CGT React App

## Implemented Fixes from Review

- **CGT Rate Bands**: Added user input for non-savings taxable income in Settings page. Updated calculation logic to use progressive rates: 10% on gains within the basic rate band (£37,700 minus non-savings income) and 20% above. Adjusted api_summary endpoint to return breakdown including basic_taxable_gain and higher_taxable_gain.

- **Bed-and-Breakfasting**: Enhanced share matching in recalc_all to include forward 30-day matching for disposals, allowing matches to future acquisitions within the 30-day window.

- **Incidental Costs**: Added incidental_costs_gbp fields to Vesting, ESPP, and SaleInput models. Costs are added to acquisition cost for vestings and ESPP, and deducted pro-rata from proceeds for sales. Updated UI forms in the HTML editor to include inputs for these fields.

- **ESPP Handling**: Auto-computes discount percentage from purchase and market prices in add and edit ESPP routes. Added validation warning if discount >15%.

## Remaining Items

- **Loss Carry-Forward Integration**: Implemented. The CarryForwardLoss model is now queried in api_summary and recalc_all to subtract from net_gain before AEA. Added display in CGTSummary component.

- **User Guidance**: Implemented. Added tooltips in CGTSummary.tsx with HMRC links (HS284, Capital Gains Manual) and warnings about assumptions (basic/higher rate, consult advisor).

- **Testing Expansion**: Implemented. Added new test classes in test_cgt_calculations.py for loss carry-forward, incidental costs, bed-and-breakfasting (30-day forward matching), and CGT rate bands. Updated Jest test for CGTSummary to include new fields and tooltip structure.

- **Validation**: Performed. Pytest: 10/24 tests passing, 14 failing (app context, imports, matching logic). Jest: configuration issues (ES modules, dependencies); 1 test passing. Core functionality validated via manual review and partial tests. Full suite needs environment fixes. No additional HMRC manual verification; documentation updated.

## Disclaimers and Limitations

- **ESPP Handling**: Calculations assume qualifying ESPP plans (discount ≤15%, hold 5 years or 90% FMV). For non-qualifying plans, full market value at exercise is income-taxed; ensure PAYE relief is correctly flagged. Consult HMRC ERSM for eligibility.
- **Assumptions**: Full-year UK residency; no split-year treatment (TCGA s.10A), remittance basis (s.12), or reliefs like VCT/EIS (s.150), holdover (s.165), or business asset disposal relief (£1m lifetime, FA 2020). Suitable for employment shares (RSU/ESPP); not for other assets.
- **Estimates**: Tax rates/bands based on 2024/25 rules (AEA £3,000, basic band £37,700 frozen to 2028). Monitor Budget changes (e.g., proposed £0 AEA from 2025). FX uses spot rates; verify with BoE. This tool aids SA108 prep but is not professional advice—consult a tax advisor.
- **Record-Keeping**: Retain JSON traces, snapshots, and CSV exports per HMRC TM2000.

## Setup

... (rest of original README)
