import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, TextField, Button, MenuItem, Select, FormControl, InputLabel, Switch, FormControlLabel, Box, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton,
  Stepper, Step, StepLabel, StepContent, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle
} from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import {
  fetchFragments, fetchSnapshot, fetchSummary,
  createVesting, getVestings, updateVesting, deleteVesting,
  createEspp, getEspp, updateEspp, deleteEspp,
  createSale, getSales, updateSale, deleteSale
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

const EditorForm = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [type, setType] = useState<'rsu' | 'espp' | 'sale'>('rsu');
  const [form, setForm] = useState<any>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [computedDiscount, setComputedDiscount] = useState(0);
  const [qualifying, setQualifying] = useState(true);
  const [errors, setErrors] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [vestings, setVestings] = useState<any[]>([]);
  const [espps, setEspps] = useState<any[]>([]);
  const [sales, setSales] = useState<any[]>([]);
  const [confirmDialog, setConfirmDialog] = useState<{open: boolean, id: number, entryType: 'rsu' | 'espp' | 'sale'}>({open: false, id: 0, entryType: 'rsu'});

  const steps = ['Basics', 'Details', 'Review & Submit'];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [v, e, s] = await Promise.all([getVestings(), getEspp(), getSales()]);
        setVestings(v);
        setEspps(e);
        setSales(s);
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
      alert('Date and quantity required');
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
      await fetchFragments(); // Trigger recalc
      alert('Deleted successfully');
    } catch (err) {
      alert('Error deleting');
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

  const handleSubmit = async () => {
    if (!form.date || !form.quantity) {
      setErrors('Date and quantity required');
      return;
    }
    if (errors) {
      alert(errors);
      return;
    }
    setLoading(true);
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
      await fetchFragments();
      await fetchSummary('2023');
      alert(editingId ? 'Updated successfully' : 'Created and recalculated!');
      setForm({});
      setEditingId(null);
      setActiveStep(0);
      setErrors('');
    } catch (err: any) {
      console.error(err);
      setErrors(err.message || 'Error submitting');
      alert(err.message || 'Error submitting');
    } finally {
      setLoading(false);
    }
  };

  const getStepContent = (step: number) => {
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
          </Box>
        );
      case 1:
        return (
          <Box sx={{ mt: 2 }}>
            {type === 'rsu' && (
              <>
                <TextField
                  label="USD Value"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.value || ''}
                  onChange={(e) => handleChange('value', parseFloat(e.target.value))}
                />
                <TextField
                  label="Shares Sold"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.shares_sold || ''}
                  onChange={(e) => handleChange('shares_sold', parseFloat(e.target.value))}
                />
              </>
            )}
            {type === 'espp' && (
              <>
                <TextField
                  label="Purchase Price USD"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.purchase_price_usd || ''}
                  onChange={(e) => handleChange('purchase_price_usd', parseFloat(e.target.value))}
                />
                <TextField
                  label="Market Price USD"
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
                {/* Simple Preview */}
                {form.quantity && form.purchase_price_usd && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2">Preview Cost Basis (est. using current rate 1.3):</Typography>
                    <Typography>USD Total: ${(form.quantity * parseFloat(form.purchase_price_usd || '0')).toFixed(2)}</Typography>
                    <Typography>GBP Total: £{((form.quantity * parseFloat(form.purchase_price_usd || '0')) / 1.3 + (form.paye_tax_gbp || 0) + (form.incidental_costs_gbp || 0)).toFixed(2)}</Typography>
                    <Typography>Per Share: £{((form.quantity * parseFloat(form.purchase_price_usd || '0')) / 1.3 / form.quantity + (form.paye_tax_gbp || 0) / form.quantity).toFixed(2)}</Typography>
                  </Box>
                )}
              </>
            )}
            {type === 'sale' && (
              <>
                <TextField
                  label="Sale Price USD"
                  type="number"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={form.sale_price_usd || ''}
                  onChange={(e) => handleChange('sale_price_usd', parseFloat(e.target.value))}
                />
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
              {type === 'rsu' && <Typography>USD Value: £{form.value ? (form.value * (form.exchange_rate || 1)).toFixed(2) : 'N/A'}</Typography>}
              {type === 'espp' && <Typography>Discount: {computedDiscount.toFixed(2)}% (Qualifying: {qualifying ? 'Yes' : 'No'})</Typography>}
              {form.incidental_costs_gbp && <Typography>Incidental Costs: £{form.incidental_costs_gbp.toFixed(2)}</Typography>}
            </Box>
          </Box>
        );
      default:
        return null;
    }
  };

  const entries = type === 'rsu' ? vestings : type === 'espp' ? espps : sales;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <Box sx={{ mt: 4 }}>
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
      </Box>

      <Box sx={{ mt: 4 }}>
        <Typography variant="h6">Existing Entries ({type.toUpperCase()})</Typography>
        <TableContainer component={Paper} sx={{ mt: 2 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Quantity</TableCell>
                <TableCell>Price/Value</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>{entry.date}</TableCell>
                  <TableCell>{entry.shares_vested || entry.shares_retained || entry.shares_sold}</TableCell>
                  <TableCell>{entry.price_usd || entry.purchase_price_usd || entry.sale_price_usd}</TableCell>
                  <TableCell>
                    <IconButton onClick={() => handleEdit(entry, type)} size="small">
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => handleDelete(entry.id, type)} size="small">
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
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
    </motion.div>
  );
};

export default EditorForm;