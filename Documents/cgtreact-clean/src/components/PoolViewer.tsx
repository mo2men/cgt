import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { Typography, Table, TableHead, TableRow, TableCell, TableBody } from '@mui/material';

const PoolViewer = () => {
  const { snapshots, selectedYear } = useAppStore();
  const snapshot = snapshots.find(s => s.tax_year === parseInt(selectedYear.split('-')[0]));

  if (!snapshot) return <Typography>No snapshot for {selectedYear}</Typography>;

  return (
    <>
      <Typography variant="h6">Pool Snapshot ({selectedYear})</Typography>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Source</TableCell>
            <TableCell>Quantity</TableCell>
            <TableCell>Cost (£)</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {snapshot.lots.map((lot, i) => (
            <TableRow key={i}>
              <TableCell>{lot.source}</TableCell>
              <TableCell>{lot.quantity}</TableCell>
              <TableCell>{lot.cost.toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
};

export default PoolViewer;