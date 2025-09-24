import React, { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import {
  Typography, FormControl, InputLabel, Select, MenuItem, ToggleButtonGroup, ToggleButton, Box,
  TextField, Button
} from '@mui/material';
import { updateSettings } from '../api/client';

const Settings = () => {
  const { selectedYear, setSelectedYear, mode, setMode } = useAppStore();
  const [nonSavingsIncome, setNonSavingsIncome] = useState(0);
  const [saving, setSaving] = useState(false);

  const handleSaveIncome = async () => {
    setSaving(true);
    try {
      await updateSettings('NonSavingsIncome', nonSavingsIncome);
      // Optionally update store or show success
    } catch (error) {
      console.error('Failed to save non-savings income:', error);
    }
    setSaving(false);
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>Settings</Typography>

      <FormControl fullWidth sx={{ mt: 2 }}>
        <InputLabel>Tax Year</InputLabel>
        <Select value={selectedYear} onChange={(e) => setSelectedYear(e.target.value)}>
          <MenuItem value="2023-24">2023–24</MenuItem>
          <MenuItem value="2024-25">2024–25</MenuItem>
          <MenuItem value="2025-26">2025–26</MenuItem>
        </Select>
      </FormControl>

      <Typography sx={{ mt: 3 }}>Non-savings taxable income (£)</Typography>
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'end', mt: 1 }}>
        <TextField
          type="number"
          value={nonSavingsIncome}
          onChange={(e) => setNonSavingsIncome(Number(e.target.value) || 0)}
          sx={{ flex: 1 }}
          inputProps={{ step: '100', min: '0' }}
        />
        <Button variant="contained" onClick={handleSaveIncome} disabled={saving}>
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </Box>

      <Typography sx={{ mt: 3 }}>Basic rate band threshold (£)</Typography>
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'end', mt: 1 }}>
        <TextField
          type="number"
          defaultValue={37700}
          onChange={(e) => {
            const value = Number(e.target.value) || 37700;
            updateSettings('BasicBandThreshold', value);
          }}
          sx={{ flex: 1 }}
          inputProps={{ step: '100', min: '0' }}
          helperText="Frozen at £37,700 until 2028; update for future changes."
        />
      </Box>

      <Typography sx={{ mt: 3 }}>Acquisition Cost Mode</Typography>
      <ToggleButtonGroup
        value={mode}
        exclusive
        onChange={(e, val) => val && setMode(val)}
        sx={{ mt: 1 }}
      >
        <ToggleButton value="strict">Strict</ToggleButton>
        <ToggleButton value="reconciliation">Reconciliation</ToggleButton>
      </ToggleButtonGroup>
    </Box>
  );
};

export default Settings;