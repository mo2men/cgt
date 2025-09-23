import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { DisposalFragment } from '../types/models';
import { Table, TableHead, TableRow, TableCell, TableBody, Button } from '@mui/material';

const TransactionTable = () => {
  const { fragments } = useAppStore();

  return (
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>Date</TableCell>
          <TableCell>Match Type</TableCell>
          <TableCell>Cost</TableCell>
          <TableCell>Proceeds</TableCell>
          <TableCell>Gain</TableCell>
          <TableCell>Trace</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {fragments.map((f) => (
          <TableRow key={f.id}>
            <TableCell>{f.sale_date}</TableCell>
            <TableCell>{f.match_type}</TableCell>
            <TableCell>£{f.acquisition_cost.toFixed(2)}</TableCell>
            <TableCell>£{f.proceeds.toFixed(2)}</TableCell>
            <TableCell>£{f.gain.toFixed(2)}</TableCell>
            <TableCell>
              <Button variant="outlined" size="small">View</Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default TransactionTable;