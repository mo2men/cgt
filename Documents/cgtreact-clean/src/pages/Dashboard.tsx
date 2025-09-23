import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Typography, Button, Box, FormControl, Select, MenuItem } from '@mui/material';
import { useAppStore } from '../store/useAppStore';
import {
  fetchFragments,
  fetchSnapshot,
  fetchSummary,
} from '../api/client';
import TransactionTable from '../components/TransactionTable';
import PoolViewer from '../components/PoolViewer';
import CGTSummary from '../components/CGTSummary';

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
  const { selectedYear, mode } = useAppStore();
  const setStore = useAppStore.setState;
  const [loading, setLoading] = useState(false);

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

        // Map summary to expected shape
        const mappedSummary = {
          tax_year: selectedYear,
          total_gain: summaryRes.total_gain,
          allowance_used: summaryRes.cgt_allowance_gbp,
          tax_due: summaryRes.estimated_cgt,
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
          <TransactionTable />
        </motion.div>

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