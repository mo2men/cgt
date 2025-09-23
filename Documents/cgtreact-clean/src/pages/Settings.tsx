import React from 'react';
import { useAppStore } from '../store/useAppStore';
import {
  Typography, FormControl, InputLabel, Select, MenuItem, ToggleButtonGroup, ToggleButton, Box
} from '@mui/material';

const Settings = () => {
  const { selectedYear, setSelectedYear, mode, setMode } = useAppStore();

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