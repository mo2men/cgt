import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, TextField, Button, MenuItem, Select, FormControl, InputLabel, Switch, FormControlLabel, Box, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Snackbar,
  Stepper, Step, StepLabel, StepContent, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Tabs, Tab
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, AccountBalance as AccountBalanceIcon, ShoppingCart as ShoppingCartIcon, Sell as SellIcon } from '@mui/icons-material';
import {
  fetchFragments, fetchSnapshot, fetchSummary,
  createVesting, getVestings, updateVesting, deleteVesting,
  createEspp, getEspp, updateEspp, deleteEspp,
  createSale, getSales, updateSale, deleteSale,
  getRates, uploadBoeCsv, addRate, deleteRate
} from '../api/client';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
} as const;

const itemVariants = {
  hidden: { y: 10, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: "tween" as const,
      duration: 0.4,
      ease: "easeOut" as const,
    },
  },
} as const;

const inputVariants = {
  hover: { scale: 1.02, boxShadow: "0 0 20px rgba(74, 0, 224, 0.3)" },
  focus: { scale: 1.01, boxShadow: "0 0 15px rgba(0, 212, 255, 0.4)" },
  tap: { scale: 0.98 },
} as const;

import { useAppStore } from '../store/useAppStore';

const EditorForm = ({ selectedYear }: { selectedYear: string }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [type, setType] = useState<'rsu' | 'espp' | 'sale'>('rsu');
  const [form, setForm] = useState<any>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [computedDiscount, setComputedDiscount] = useState(0);
  const [qualifying, setQualifying] = useState(true);
  const [errors, setErrors] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [vestings, setVestings] = useState<any[]>([]);
  const [espps, setEspps] = useState<any[]>([]);
  const [sales, setSales] = useState<any[]>([]);
  const [confirmDialog, setConfirmDialog] = useState<{open: boolean, id: number, entryType: 'rsu' | 'espp' | 'sale'}>({open: false, id: 0, entryType: 'rsu'});
  const [tabValue, setTabValue] = useState(0);
  const [rates, setRates] = useState<any[]>([]);
  const [rateForm, setRateForm] = useState({ date: '', rate: '' });
  const [file, setFile] = useState<File | null>(null);

  const steps = ['Basics', 'Details', 'Review & Submit'];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [v, e, s, r] = await Promise.all([getVestings(), getEspp(), getSales(), getRates()]);
        setVestings(v);
        setEspps(e);
        setSales(s);
        setRates(r);
      } catch (err) {
        console.error('Error fetching data:', err);
      }
    };
    fetchData();
  }, []);

  const handleChange = (field: string, value: any) => {
    setForm({ ...form, [field]: value });
    setErrors(''); // Clear errors on change
    if (type === 'espp' && (field === 'purchase_price_usd' || field === 'market_price_usd' || field === 'qualifying')) {
      const purchase = field === 'purchase_price_usd' ? parseFloat(value || '0') : parseFloat(form.purchase_price_usd || '0');
      const market = parseFloat(form.market_price_usd || '0');
      const isQualifying = field === 'qualifying' ? value : qualifying;
      if (market > 0 && purchase < market && purchase > 0) {
        const discount = ((market - purchase) / market) * 100;
        setComputedDiscount(discount);
        if (discount > 15 && isQualifying) {
          setErrors(`ESPP discount ${discount.toFixed(2)}% > 15%. For qualifying plans, discount must be ≤15%. Set qualifying to false for non-qualifying plans.`);
        }
        setQualifying(isQualifying);
      } else {
        setComputedDiscount(0);
        setQualifying(true);
      }
    }
  };

  const handleNext = () => {
    if (activeStep === 0 && (!form.date || !form.quantity)) {
      setErrors('Date and quantity required');
      return;
    }
    if (activeStep < steps.length - 1) {
      setActiveStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handleEdit = (entry: any, entryType: 'rsu' | 'espp' | 'sale') => {
    setType(entryType);
    setEditingId(entry.id);
    setForm({
      date: entry.date,
      quantity: entry.shares_vested || entry.shares_retained || entry.shares_sold,
      value: entry.price_usd || entry.purchase_price_usd || entry.sale_price_usd,
      shares_sold: entry.shares_sold,
      purchase_price_usd: entry.purchase_price_usd,
      market_price_usd: entry.market_price_usd,
      discount_taxed_paye: entry.discount_taxed_paye,
      paye_tax_gbp: entry.paye_tax_gbp,
      tax_paid_gbp: entry.tax_paid_gbp,
      exchange_rate: entry.exchange_rate,
      incidental_costs_gbp: entry.incidental_costs_gbp,
      notes: entry.notes,
    });
    if (entryType === 'espp') {
      const purchase = entry.purchase_price_usd || 0;
      const market = entry.market_price_usd || 0;
      if (market > 0 && purchase < market) {
        setComputedDiscount(((market - purchase) / market) * 100);
        setQualifying(entry.qualifying);
      }
    }
    setActiveStep(0);
  };

  const performDelete = async (id: number, entryType: 'rsu' | 'espp' | 'sale') => {
    try {
      let res;
      if (entryType === 'rsu') res = await deleteVesting(id);
      else if (entryType === 'espp') res = await deleteEspp(id);
      else res = await deleteSale(id);
      // Refetch data
      const [v, e, s] = await Promise.all([getVestings(), getEspp(), getSales()]);
      setVestings(v);
      setEspps(e);
      setSales(s);
      await fetchFragments(selectedYear.split('-')[0]); // Trigger recalc
      setSuccess('Deleted successfully');
    } catch (err) {
      setErrors('Error deleting');
    }
  };

  const handleDelete = (id: number, entryType: 'rsu' | 'espp' | 'sale') => {
    setConfirmDialog({ open: true, id, entryType });
  };

  const handleConfirmDelete = () => {
    performDelete(confirmDialog.id, confirmDialog.entryType);
    setConfirmDialog({ open: false, id: 0, entryType: 'rsu' });
  };

  const handleCancelDelete = () => {
    setConfirmDialog({ open: false, id: 0, entryType: 'rsu' });
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleUploadCsv = async () => {
    if (!file) return;
    try {
      await uploadBoeCsv(file);
      setFile(null);
      const r = await getRates();
      setRates(r);
      setSuccess('CSV uploaded successfully');
    } catch (err) {
      setErrors('Error uploading CSV');
    }
  };

  const handleAddRate = async () => {
    if (!rateForm.date || !rateForm.rate) {
      setErrors('Date and rate required');
      return;
    }
    try {
      await addRate({ date: rateForm.date, rate: parseFloat(rateForm.rate) });
      setRateForm({ date: '', rate: '' });
      const r = await getRates();
      setRates(r);
      setSuccess('Rate added successfully');
    } catch (err) {
      setErrors('Error adding rate');
    }
  };

  const handleDeleteRate = async (id: number) => {
    try {
      await deleteRate(id);
      const r = await getRates();
      setRates(r);
      setSuccess('Rate deleted successfully');
    } catch (err) {
      setErrors('Error deleting rate');
    }
  };

  const handleSubmit = async () => {
    if (!form.date || !form.quantity) {
      setErrors('Date and quantity required');
      return;
    }
    if (errors) {
      return;
    }
    setLoading(true);
    setErrors('');
    setSuccess('');
    try {
      let res;
      if (editingId) {
        // Update
        if (type === 'rsu') {
          res = await updateVesting(editingId, {
            ...form,
            shares_vested: form.quantity,
            shares_sold: form.shares_sold || 0,
          });
        } else if (type === 'espp') {
          res = await updateEspp(editingId, {
            ...form,
            shares_retained: form.quantity,
            qualifying,
          });
        } else {
          res = await updateSale(editingId, {
            ...form,
            shares_sold: form.quantity,
          });
        }
      } else {
        // Create
        if (type === 'rsu') {
          res = await createVesting({
            ...form,
            shares_vested: form.quantity,
            shares_sold: form.shares_sold || 0,
          });
        } else if (type === 'espp') {
          res = await createEspp({
            ...form,
            shares_retained: form.quantity,
            qualifying,
          });
        } else {
          res = await createSale({
            ...form,
            shares_sold: form.quantity,
          });
        }
      }
      // Refetch data
      const [v, e, s] = await Promise.all([getVestings(), getEspp(), getSales()]);
      setVestings(v);
      setEspps(e);
      setSales(s);
      // Trigger recalc
      await fetchFragments(selectedYear);
      await fetchSummary(parseInt(selectedYear.split('-')[0]));
      await fetchFragments(selectedYear.split('-')[0]);
      setSuccess(editingId ? 'Updated successfully' : 'Created and recalculated!');
      setForm({});
      setEditingId(null);
      setActiveStep(0);
    } catch (err: any) {
      console.error(err);
      const errorMsg = err.message || 'Error submitting';
      setErrors(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const getStepContent = (step: number) => {
    const exchangeRate = form.exchange_rate || 1.3; // Default preview rate
    const quantity = parseFloat(form.quantity || '0');
    const getPreview = () => {
      if (type === 'rsu' && quantity > 0 && form.value) {
        const totalUsd = quantity * parseFloat(form.value || '0');
        const totalGbp = totalUsd / exchangeRate + (form.tax_paid_gbp || 0) + (form.incidental_costs_gbp || 0);
        const netShares = quantity - (form.shares_sold || 0);
        const avgCost = totalGbp / netShares;
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2">Preview (est. rate {exchangeRate}):</Typography>
            <Typography>USD Total: ${totalUsd.toFixed(2)}</Typography>
            <Typography>GBP Total (inc. tax/incidental): £{totalGbp.toFixed(2)}</Typography>
            <Typography>Net Shares: {netShares.toFixed(6)}</Typography>
            <Typography>Per Share Cost: £{avgCost.toFixed(2)}</Typography>
          </Box>
        );
      } else if (type === 'espp' && quantity > 0 && form.purchase_price_usd) {
        const totalUsd = quantity * parseFloat(form.purchase_price_usd || '0');
        const totalGbp = totalUsd / exchangeRate + (form.paye_tax_gbp || 0) + (form.incidental_costs_gbp || 0);
        const avgCost = totalGbp / quantity;
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2">Preview Cost Basis (est. rate {exchangeRate}):</Typography>
            <Typography>USD Total: ${totalUsd.toFixed(2)}</Typography>
            <Typography>GBP Total (inc. PAYE/incidental): £{totalGbp.toFixed(2)}</Typography>
            <Typography>Per Share: £{avgCost.toFixed(2)}</Typography>
          </Box>
        );
      } else if (type === 'sale' && quantity > 0 && form.sale_price_usd) {
        const proceedsUsd = quantity * parseFloat(form.sale_price_usd || '0');
        const proceedsGbp = proceedsUsd / exchangeRate - (form.incidental_costs_gbp || 0);
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2">Preview Proceeds (est. rate {exchangeRate}):</Typography>
            <Typography>USD Total: ${proceedsUsd.toFixed(2)}</Typography>
            <Typography>GBP Proceeds (net incidental): £{proceedsGbp.toFixed(2)}</Typography>
            <Typography>Per Share: £{(proceedsGbp / quantity).toFixed(2)}</Typography>
          </Box>
        );
      }
      return null;
    };

    switch (step) {
      case 0:
        return (
          <Box sx={{ mt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Type</InputLabel>
              <Select
                value={type}
                onChange={(e) => setType(e.target.value as any)}
                sx={{
                  transition: 'all 0.3s ease',
                  '&:hover': { boxShadow: '0 0 15px rgba(74, 0, 224, 0.2)' }
                }}
              >
                <MenuItem value="rsu">RSU Vesting</MenuItem>
                <MenuItem value="espp">ESPP Purchase</MenuItem>
                <MenuItem value="sale">Sale</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Date"
              type="date"
              fullWidth
              sx={{ mt: 2 }}
              InputLabelProps={{ shrink: true }}
              value={form.date || ''}
              onChange={(e) => handleChange('date', e.target.value)}
            />
            <TextField
              label="Quantity"
              type="number"
              fullWidth
              sx={{ mt: 2 }}
              value={form.quantity || ''}
              onChange={(e) => handleChange('quantity', parseFloat(e.target.value))}
            />
            {getPreview()}
          </Box>
        );
      case 1:
        return (
          <Box sx={{ mt: 2 }}>
            {type === 'rsu' && (
              <>
                <TextField
                  label="Price USD (per share)"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.value || ''}
                  onChange={(e) => handleChange('value', parseFloat(e.target.value))}
                />
                <TextField
                  label="Shares Sold for Tax"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.shares_sold || ''}
                  onChange={(e) => handleChange('shares_sold', parseFloat(e.target.value))}
                />
                <TextField
                  label="Tax Paid GBP"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.tax_paid_gbp || ''}
                  onChange={(e) => handleChange('tax_paid_gbp', parseFloat(e.target.value))}
                />
                {getPreview()}
              </>
            )}
            {type === 'espp' && (
              <>
                <TextField
                  label="Purchase Price USD (per share)"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.purchase_price_usd || ''}
                  onChange={(e) => handleChange('purchase_price_usd', parseFloat(e.target.value))}
                />
                <TextField
                  label="Market Price USD (per share)"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.market_price_usd || ''}
                  onChange={(e) => handleChange('market_price_usd', parseFloat(e.target.value))}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={qualifying}
                      onChange={(e) => handleChange('qualifying', e.target.checked)}
                    />
                  }
                  label="Qualifying ESPP Plan (discount ≤15%, hold periods met)"
                  sx={{ mt: 2 }}
                />
                {computedDiscount > 0 && (
                  <Alert severity={qualifying && computedDiscount > 15 ? "error" : "warning"} sx={{ mt: 2 }}>
                    ESPP discount {computedDiscount.toFixed(2)}%. {qualifying && computedDiscount > 15 ? "Non-qualifying: Full market value income-taxed. Set to false or adjust." : "Qualifying if ≤15%. Consult HMRC ERSM for eligibility."}
                  </Alert>
                )}
                {errors && <Alert severity="error" sx={{ mt: 2 }}>{errors}</Alert>}
                <FormControlLabel
                  control={
                    <Switch
                      checked={form.discount_taxed_paye || false}
                      onChange={(e) => handleChange('discount_taxed_paye', e.target.checked)}
                    />
                  }
                  label="Discount taxed under PAYE"
                  sx={{ mt: 2 }}
                />
                <TextField
                  label="PAYE Tax GBP"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.paye_tax_gbp || ''}
                  onChange={(e) => handleChange('paye_tax_gbp', parseFloat(e.target.value))}
                />
                <TextField
                  label="Tax Paid GBP"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.tax_paid_gbp || ''}
                  onChange={(e) => handleChange('tax_paid_gbp', parseFloat(e.target.value))}
                />
                {getPreview()}
              </>
            )}
            {type === 'sale' && (
              <>
                <TextField
                  label="Sale Price USD (per share)"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.sale_price_usd || ''}
                  onChange={(e) => handleChange('sale_price_usd', parseFloat(e.target.value))}
                />
                {getPreview()}
              </>
            )}
          </Box>
        );
      case 2:
        return (
          <Box sx={{ mt: 2 }}>
            <TextField
              label="Exchange Rate (USD→GBP)"
              type="number"
              fullWidth
              sx={{ mt: 2 }}
              value={form.exchange_rate || ''}
              onChange={(e) => handleChange('exchange_rate', parseFloat(e.target.value))}
              helperText="Leave blank to use auto FX from BoE rates"
            />
            <TextField
              label="Incidental Costs GBP"
              type="number"
              fullWidth
              sx={{ mt: 2 }}
              value={form.incidental_costs_gbp || ''}
              onChange={(e) => handleChange('incidental_costs_gbp', parseFloat(e.target.value))}
            />
            <TextField
              label="Notes"
              multiline
              rows={3}
              fullWidth
              sx={{ mt: 2 }}
              value={form.notes || ''}
              onChange={(e) => handleChange('notes', e.target.value)}
            />
            <Box sx={{ mt: 3 }}>
              <Typography variant="h6">Preview</Typography>
              <Typography>Type: {type.toUpperCase()}</Typography>
              <Typography>Date: {form.date || 'N/A'}</Typography>
              <Typography>Quantity: {form.quantity || 'N/A'}</Typography>
              {type === 'rsu' && form.value && <Typography>USD Value: ${ (form.quantity * parseFloat(form.value || '0')).toFixed(2) } → GBP est. £{ (form.quantity * parseFloat(form.value || '0') / exchangeRate).toFixed(2) }</Typography>}
              {type === 'espp' && <Typography>Discount: {computedDiscount.toFixed(2)}% (Qualifying: {qualifying ? 'Yes' : 'No'})</Typography>}
              {form.incidental_costs_gbp && <Typography>Incidental Costs: £{form.incidental_costs_gbp.toFixed(2)}</Typography>}
              {getPreview()}
            </Box>
            {errors && <Alert severity="error" sx={{ mt: 2 }}>{errors}</Alert>}
          </Box>
        );
      default:
        return null;
    }
  };

  const allEntries = [
    ...vestings.map(v => ({ ...v, entryType: 'rsu' })),
    ...espps.map(e => ({ ...e, entryType: 'espp' })),
    ...sales.map(s => ({ ...s, entryType: 'sale' }))
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <Box sx={{ mt: 4 }}>
        <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
          <Tab label="Transactions" />
          <Tab label="Exchange Rates" />
        </Tabs>
        {tabValue === 0 && (
          <>
            <motion.div variants={itemVariants}>
              <Typography variant="h5">Add Transaction Wizard</Typography>
            </motion.div>

            <Stepper activeStep={activeStep} sx={{ mt: 4 }}>
              {steps.map((label, index) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                  <StepContent>
                    {getStepContent(index)}
                    <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
                      <Button
                        disabled={activeStep === 0}
                        onClick={handleBack}
                      >
                        Back
                      </Button>
                      <Button
                        variant="contained"
                        onClick={activeStep === steps.length - 1 ? handleSubmit : handleNext}
                        disabled={loading || !!errors}
                      >
                        {activeStep === steps.length - 1 ? 'Submit & Recalculate' : 'Next'}
                      </Button>
                    </Box>
                  </StepContent>
                </Step>
              ))}
            </Stepper>

            {activeStep === steps.length && (
              <Paper square elevation={0} sx={{ p: 3 }}>
                <Typography>All steps completed!</Typography>
                <Button onClick={() => setActiveStep(0)}>Reset</Button>
              </Paper>
            )}

            <Box sx={{ mt: 4 }}>
              <Typography variant="h6">All Existing Entries</Typography>
              <TableContainer component={Paper} sx={{ mt: 2, borderRadius: 2, overflow: 'hidden' }}>
                <Table sx={{ minWidth: 650 }}>
                  <TableHead>
                    <TableRow>
                      <TableCell>Type</TableCell>
                      <TableCell>Date</TableCell>
                      <TableCell>Shares</TableCell>
                      <TableCell>USD Price/Value</TableCell>
                      <TableCell>Tax Paid GBP</TableCell>
                      <TableCell>Incidental GBP</TableCell>
                      <TableCell>Exchange Rate</TableCell>
                      <TableCell>Notes</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {allEntries.map((entry) => {
                      const icon = entry.entryType === 'rsu' ? <AccountBalanceIcon /> : entry.entryType === 'espp' ? <ShoppingCartIcon /> : <SellIcon />;
                      return (
                        <TableRow key={`${entry.entryType}-${entry.id}`} sx={{ '&:nth-of-type(odd)': { backgroundColor: '#fafafa' }, '&:hover': { backgroundColor: '#e0e0e0' } }}>
                          <TableCell>{icon} {entry.entryType.toUpperCase()}</TableCell>
                          <TableCell>{entry.date}</TableCell>
                          <TableCell>{(entry.shares_vested || entry.shares_retained || entry.shares_sold || 0).toFixed(6)}</TableCell>
                          <TableCell>${(entry.price_usd || entry.purchase_price_usd || entry.sale_price_usd || 0).toFixed(2)}</TableCell>
                          <TableCell>£{(entry.tax_paid_gbp || entry.paye_tax_gbp || 0).toFixed(2)}</TableCell>
                          <TableCell>£{(entry.incidental_costs_gbp || 0).toFixed(2)}</TableCell>
                          <TableCell>{entry.exchange_rate || ''}</TableCell>
                          <TableCell>{entry.notes || ''}</TableCell>
                          <TableCell>
                            <IconButton onClick={() => handleEdit(entry, entry.entryType)} size="small" color="primary">
                              <EditIcon />
                            </IconButton>
                            <IconButton onClick={() => handleDelete(entry.id, entry.entryType)} size="small" color="error">
                              <DeleteIcon />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          </>
        )}

        {tabValue === 1 && (
          <Box>
            <Typography variant="h6">Upload Bank of England CSV</Typography>
            <input type="file" accept=".csv" onChange={handleFileChange} />
            <Button onClick={handleUploadCsv} disabled={!file}>Upload CSV</Button>
            <a href="https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp?Travel=NIxIRxRSxSUx&FromSeries=1&ToSeries=50&DAT=RNG&FD=1&FM=Jan&FY=2020&TD=31&TM=Dec&TY=2025&FNY=&CSVF=TT&html.x=265&html.y=40&C=C8P&Filter=N#" target="_blank" rel="noopener noreferrer">Download BoE CSV</a>
            <Typography variant="h6" sx={{ mt: 2 }}>Add Rate Manually</Typography>
            <TextField label="Date" type="date" value={rateForm.date} onChange={(e) => setRateForm({ ...rateForm, date: e.target.value })} InputLabelProps={{ shrink: true }} />
            <TextField label="Rate" type="number" inputProps={{ step: "0.000001" }} value={rateForm.rate} onChange={(e) => setRateForm({ ...rateForm, rate: e.target.value })} />
            <Button onClick={handleAddRate}>Add Rate</Button>
            <Typography variant="h6" sx={{ mt: 2 }}>Existing Rates</Typography>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>USD→GBP</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rates.map((rate) => (
                    <TableRow key={rate.id}>
                      <TableCell>{rate.date}</TableCell>
                      <TableCell>{rate.usd_gbp}</TableCell>
                      <TableCell>
                        <IconButton onClick={() => handleDeleteRate(rate.id)} size="small">
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </Box>

      <Dialog
        open={confirmDialog.open}
        onClose={handleCancelDelete}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Are you sure you want to delete this entry?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelDelete} color="primary">
            Cancel
          </Button>
          <Button onClick={handleConfirmDelete} color="error" autoFocus>
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess('')}
        message={success}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </motion.div>
  );
};

export default EditorForm;