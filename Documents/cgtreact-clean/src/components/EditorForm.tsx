import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, TextField, Button, MenuItem, Select, FormControl, InputLabel, Switch, FormControlLabel, Box, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton
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
  const [type, setType] = useState<'rsu' | 'espp' | 'sale'>('rsu');
  const [form, setForm] = useState<any>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [computedDiscount, setComputedDiscount] = useState(0);
  const [qualifying, setQualifying] = useState(true);
  const [loading, setLoading] = useState(false);
  const [vestings, setVestings] = useState<any[]>([]);
  const [espps, setEspps] = useState<any[]>([]);
  const [sales, setSales] = useState<any[]>([]);

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
    if (type === 'espp' && (field === 'purchase_price_usd' || field === 'market_price_usd')) {
      const purchase = parseFloat(form.purchase_price_usd || '0') || parseFloat(value || '0');
      const market = parseFloat(form.market_price_usd || '0');
      if (market > 0 && purchase < market && purchase > 0) {
        const discount = ((market - purchase) / market) * 100;
        setComputedDiscount(discount);
        setQualifying(discount <= 15);
      } else {
        setComputedDiscount(0);
        setQualifying(true);
      }
    }
  };

  const handleEdit = (entry: any, entryType: 'rsu' | 'espp' | 'sale') => {
    setType(entryType);
    setEditingId(entry.id);
    setForm({
      date: entry.date,
      shares_vested: entry.shares_vested || entry.shares_retained || entry.shares_sold,
      price_usd: entry.price_usd || entry.purchase_price_usd || entry.sale_price_usd,
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
  };

  const handleDelete = async (id: number, entryType: 'rsu' | 'espp' | 'sale') => {
    if (!confirm('Are you sure?')) return;
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

  const handleSubmit = async () => {
    if (!form.date || !form.quantity) {
      alert('Date and quantity required');
      return;
    }
    setLoading(true);
    try {
      let res;
      if (editingId) {
        // Update
        if (type === 'rsu') res = await updateVesting(editingId, form);
        else if (type === 'espp') res = await updateEspp(editingId, form);
        else res = await updateSale(editingId, form);
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
    } catch (err) {
      console.error(err);
      alert('Error submitting');
    } finally {
      setLoading(false);
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
          <Typography variant="h5">Add Transaction</Typography>
        </motion.div>

        <motion.div variants={itemVariants}>
          <FormControl fullWidth sx={{ mt: 2 }}>
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
        </motion.div>

        <motion.div variants={itemVariants}>
          <TextField
            label="Date"
            type="date"
            fullWidth
            sx={{ 
              mt: 2,
              transition: 'all 0.3s ease',
              '& .MuiInputBase-root': {
                transition: 'all 0.3s ease',
                '&:hover': { boxShadow: '0 0 10px rgba(0, 212, 255, 0.2)' },
                '&.Mui-focused': { boxShadow: '0 0 20px rgba(74, 0, 224, 0.3)' },
              },
            }}
            InputLabelProps={{ shrink: true }}
            value={form.date || ''}
            onChange={(e) => handleChange('date', e.target.value)}
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <TextField
            label="Quantity"
            type="number"
            fullWidth
            sx={{ 
              mt: 2,
              transition: 'all 0.3s ease',
              '& .MuiInputBase-root': {
                transition: 'all 0.3s ease',
                '&:hover': { boxShadow: '0 0 10px rgba(0, 212, 255, 0.2)' },
                '&.Mui-focused': { boxShadow: '0 0 20px rgba(74, 0, 224, 0.3)' },
              },
            }}
            value={form.quantity || ''}
            onChange={(e) => handleChange('quantity', parseFloat(e.target.value))}
          />
        </motion.div>

        {type === 'rsu' && (
          <motion.div variants={itemVariants}>
            <TextField
              label="USD Value"
              type="number"
              fullWidth
              sx={{
                mt: 2,
                transition: 'all 0.3s ease',
                '& .MuiInputBase-root': {
                  transition: 'all 0.3s ease',
                  '&:hover': { boxShadow: '0 0 10px rgba(0, 212, 255, 0.2)' },
                  '&.Mui-focused': { boxShadow: '0 0 20px rgba(74, 0, 224, 0.3)' },
                },
              }}
              value={form.value || ''}
              onChange={(e) => handleChange('value', parseFloat(e.target.value))}
            />
          </motion.div>
        )}

        {type === 'espp' && (
          <>
            <motion.div variants={itemVariants}>
              <TextField
                label="Purchase Price USD"
                type="number"
                fullWidth
                sx={{
                  mt: 2,
                  transition: 'all 0.3s ease',
                  '& .MuiInputBase-root': {
                    transition: 'all 0.3s ease',
                    '&:hover': { boxShadow: '0 0 10px rgba(0, 212, 255, 0.2)' },
                    '&.Mui-focused': { boxShadow: '0 0 20px rgba(74, 0, 224, 0.3)' },
                  },
                }}
                value={form.purchase_price_usd || ''}
                onChange={(e) => handleChange('purchase_price_usd', parseFloat(e.target.value))}
              />
            </motion.div>
            <motion.div variants={itemVariants}>
              <TextField
                label="Market Price USD"
                type="number"
                fullWidth
                sx={{
                  mt: 2,
                  transition: 'all 0.3s ease',
                  '& .MuiInputBase-root': {
                    transition: 'all 0.3s ease',
                    '&:hover': { boxShadow: '0 0 10px rgba(0, 212, 255, 0.2)' },
                    '&.Mui-focused': { boxShadow: '0 0 20px rgba(74, 0, 224, 0.3)' },
                  },
                }}
                value={form.market_price_usd || ''}
                onChange={(e) => handleChange('market_price_usd', parseFloat(e.target.value))}
              />
            </motion.div>
            {!qualifying && (
              <motion.div variants={itemVariants}>
                <Alert severity="warning" sx={{ mt: 2 }}>
                  ESPP discount {computedDiscount.toFixed(2)}% &gt; 15%. This may not qualify for relief. Full market value at exercise is treated as income; ensure PAYE is correctly flagged. Consult HMRC ERSM.
                </Alert>
              </motion.div>
            )}
          </>
        )}

        <motion.div variants={itemVariants}>
          <TextField
            label="Exchange Rate (USD→GBP)"
            type="number"
            fullWidth
            sx={{ 
              mt: 2,
              transition: 'all 0.3s ease',
              '& .MuiInputBase-root': {
                transition: 'all 0.3s ease',
                '&:hover': { boxShadow: '0 0 10px rgba(0, 212, 255, 0.2)' },
                '&.Mui-focused': { boxShadow: '0 0 20px rgba(74, 0, 224, 0.3)' },
              },
            }}
            value={form.fx || ''}
            onChange={(e) => handleChange('fx', parseFloat(e.target.value))}
          />
        </motion.div>

        {type === 'sale' && (
          <motion.div variants={itemVariants}>
            <TextField
              label="Proceeds (GBP)"
              type="number"
              fullWidth
              sx={{ 
                mt: 2,
                transition: 'all 0.3s ease',
                '& .MuiInputBase-root': {
                  transition: 'all 0.3s ease',
                  '&:hover': { boxShadow: '0 0 10px rgba(0, 212, 255, 0.2)' },
                  '&.Mui-focused': { boxShadow: '0 0 20px rgba(74, 0, 224, 0.3)' },
                },
              }}
              value={form.proceeds || ''}
              onChange={(e) => handleChange('proceeds', parseFloat(e.target.value))}
            />
          </motion.div>
        )}

        {type === 'espp' && (
          <motion.div variants={itemVariants}>
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
          </motion.div>
        )}

        <motion.div variants={itemVariants}>
          <motion.div
            variants={inputVariants}
            whileHover="hover"
            whileFocus="focus"
            whileTap="tap"
          >
            <Button
              variant="contained"
              sx={{ mt: 3 }}
              onClick={handleSubmit}
              disabled={loading}
            >
              Submit & Recalculate
            </Button>
          </motion.div>
        </motion.div>
      </Box>
    </motion.div>
  );
};

export default EditorForm;