import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Typography, Button, Box, FormControl, Select, MenuItem } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';
import {
  fetchFragments,
  fetchSnapshot,
  fetchSummary,
} from '../api/client';
import TransactionTable from '../components/TransactionTable';
import PoolViewer from '../components/PoolViewer';
import CGTSummary from '../components/CGTSummary';
import TraceModel from '../components/TraceModel';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2,
      delayChildren: 0.1,
    },
  },
} as const;

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: "tween" as const,
      duration: 0.5,
      ease: "easeOut" as const,
    },
  },
} as const;

const loadingVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
} as const;

const Dashboard = () => {
  const { selectedYear, mode, selectedFragment, setSelectedFragment } = useAppStore();
  const setStore = useAppStore.setState;
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const years = ['2022-23', '2023-24', '2024-25', '2025-26'];

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const yearNum = parseInt(selectedYear.split('-')[0]);
        const [fragmentsRes, snapshotRes, summaryRes] = await Promise.all([
          fetchFragments(),
          fetchSnapshot(yearNum.toString()),
          fetchSummary(yearNum.toString()),
        ]);

        // Map fragments to expected shape
        const mappedFragments = fragmentsRes.items.map((f: any) => ({
          id: f.disposal_id,
          sale_date: f.sale_date,
          match_type: f.matching_type,
          acquisition_cost: f.avg_cost_gbp * f.matched_shares,
          proceeds: f.proceeds_gbp,
          gain: f.gain_gbp,
        }));

        // Map snapshot: parse snapshot_json to lots
        const snapshot = snapshotRes;
        const perSaleSnaps = JSON.parse(snapshot.snapshot_json || '[]');
        const lastSnap = perSaleSnaps[perSaleSnaps.length - 1] || { pool_after: [] };
        const poolAfter = lastSnap.pool_after || [];
        const lots = poolAfter.map((lot: any) => ({
          source: lot.source,
          quantity: lot.remaining,
          cost: lot.per_share_cost * lot.remaining,
        }));
        const mappedSnapshot = {
          ...snapshot,
          tax_year: selectedYear,
          lots,
        };

        // Map summary to expected shape using backend fields
        const backendSummary = summaryRes;
        const mappedSummary = {
          tax_year: selectedYear,
          tax_year_start: backendSummary.tax_year_start,
          tax_year_end: backendSummary.tax_year_end,
          cgt_allowance_gbp: backendSummary.cgt_allowance_gbp || 0,
          carry_forward_loss_gbp: backendSummary.carry_forward_loss_gbp || 0,
          net_gain_after_losses: backendSummary.net_gain_after_losses || backendSummary.net_gain || 0,
          non_savings_income: backendSummary.non_savings_income || 0,
          basic_threshold: backendSummary.basic_threshold || 37700,
          basic_band_available: backendSummary.basic_band_available || 0,
          total_disposals: backendSummary.total_disposals || 0,
          total_proceeds: backendSummary.total_proceeds || 0,
          total_cost: backendSummary.total_cost || 0,
          total_gain: backendSummary.total_gain || 0,
          pos: backendSummary.pos || 0,
          neg: backendSummary.neg || 0,
          net_gain: backendSummary.net_gain || 0,
          taxable_after_allowance: backendSummary.taxable_after_allowance || 0,
          basic_taxable_gain: backendSummary.basic_taxable_gain || 0,
          higher_taxable_gain: backendSummary.higher_taxable_gain || 0,
          estimated_cgt: backendSummary.estimated_cgt || 0,
        };

        setStore({
          fragments: mappedFragments,
          snapshots: [mappedSnapshot],
          summaries: [mappedSummary],
        });
      } catch (err) {
        console.error('Error loading dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    if (selectedYear) {
      loadData();
    }
  }, [selectedYear, mode, setStore]);

  const handleExport = async () => {
    try {
      //This function is not implemented yet.  Placeholder for now.
      const res = await fetchFragments();
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'disposals.csv');
      document.body.appendChild(link);
      link.click();
    } catch (err) {
      alert('Export failed');
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
          <Typography variant="h4" gutterBottom>
            CGT Audit Dashboard
          </Typography>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Typography variant="body1" sx={{ mb: 1 }}>Select Tax Year:</Typography>
          <FormControl sx={{ mt: 2, minWidth: 120 }}>
            <Select
              value={selectedYear}
              onChange={(e) => setStore({ selectedYear: e.target.value })}
            >
              {years.map((year) => (
                <MenuItem key={year} value={year}>
                  {year}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Button
            variant="contained"
            sx={{ mt: 2 }}
            onClick={() => navigate('/editor')}
          >
            Edit Transactions
          </Button>
        </motion.div>

        <motion.div variants={itemVariants}>
          <TransactionTable />
        </motion.div>

        {selectedFragment && (
          <motion.div variants={itemVariants}>
            <Box sx={{ mt: 2, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Trace for Fragment {selectedFragment.id}</Typography>
                <Button variant="outlined" size="small" onClick={() => setSelectedFragment(null)}>
                  Close
                </Button>
              </Box>
              <TraceModel fragmentId={selectedFragment.id} />
            </Box>
          </motion.div>
        )}

        <motion.div variants={itemVariants}>
          <Button variant="outlined" sx={{ mt: 2 }} onClick={handleExport}>
            Export Disposals CSV
          </Button>
        </motion.div>

        <motion.div variants={itemVariants}>
          <PoolViewer />
        </motion.div>

        <motion.div variants={itemVariants}>
          <CGTSummary />
        </motion.div>

        {loading && (
          <motion.div
            variants={loadingVariants}
            initial="hidden"
            animate="visible"
          >
            <Box sx={{ mt: 2 }}>
              <Typography>Loading data…</Typography>
            </Box>
          </motion.div>
        )}
      </Box>
    </motion.div>
  );
};

export default Dashboard;