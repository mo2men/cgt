import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, TextField, Button, MenuItem, Select, FormControl, InputLabel, Switch, FormControlLabel, Box
} from '@mui/material';
import { fetchFragments, fetchSnapshot, fetchSummary } from '../api/client';

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
  const [loading, setLoading] = useState(false);

  const handleChange = (field: string, value: any) => {
    setForm({ ...form, [field]: value });
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await fetchFragments();
      await fetchSummary('2023');
      alert('Submitted and recalculated!');
      setForm({});
    } catch (err) {
      alert('Error submitting');
    } finally {
      setLoading(false);
    }
  };

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

        {type !== 'sale' && (
          <motion.div variants={itemVariants}>
            <TextField
              label={type === 'rsu' ? 'USD Value' : 'Purchase Price'}
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