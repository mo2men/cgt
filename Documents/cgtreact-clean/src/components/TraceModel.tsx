import React, { useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { fetchTransaction } from '../api/client';
import { Typography, Box, List, ListItem, ListItemText, Divider, Chip, Button } from '@mui/material';

interface TransactionData {
  disposal_id: number;
  sale_date: string;
  sale_input_id: number;
  matched_date: string | null;
  matching_type: string;
  matched_shares: string;
  avg_cost_gbp: string;
  proceeds_gbp: string;
  cost_basis_gbp: string;
  gain_gbp: string;
  cgt_due_gbp: string;
  calculation: {
    inputs?: any;
    equations?: string[];
    numeric_trace?: {
      sale_price_usd?: string;
      rate_for_sale?: string;
      proceeds_total_gbp?: string;
      cost_total_gbp?: string;
      gain_gbp?: string;
      shares_matched?: string;
      fragment_index?: number;
    };
  };
  details: Array<{
    equations: string;
    explanation: string;
  }>;
}

interface TraceModelProps {
  fragmentId: number;
}

const TraceModel: React.FC<TraceModelProps> = ({ fragmentId }) => {
  const setSelectedFragment = useAppStore((state) => state.setSelectedFragment);
  const [data, setData] = useState<TransactionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTrace = async () => {
      try {
        setLoading(true);
        const transactionData = await fetchTransaction(fragmentId);
        setData(transactionData);
      } catch (err) {
        setError('Failed to load trace data');
        console.error('Error fetching trace:', err);
      } finally {
        setLoading(false);
      }
    };

    loadTrace();
  }, [fragmentId]);

  if (loading) {
    return <Typography>Loading trace...</Typography>;
  }

  if (error || !data) {
    return (
      <Box>
        <Typography color="error">{error || 'No trace data available'}</Typography>
        <Button onClick={() => setSelectedFragment(null)} variant="outlined" size="small" sx={{ mt: 1 }}>
          Close
        </Button>
      </Box>
    );
  }

  const calc = data.calculation;
  const numericTrace = calc.numeric_trace || {};

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Trace for Disposal {data.disposal_id}</Typography>
        <Button onClick={() => setSelectedFragment(null)} variant="outlined" size="small">
          Close
        </Button>
      </Box>

      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle1">Sale Details</Typography>
        <List dense>
          <ListItem>
            <ListItemText primary="Sale Date" secondary={data.sale_date} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Sale ID" secondary={data.sale_input_id} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Matched Date" secondary={data.matched_date || 'N/A'} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Matching Type" secondary={data.matching_type} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Matched Shares" secondary={parseFloat(data.matched_shares).toFixed(6)} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Avg Cost GBP" secondary={`£${parseFloat(data.avg_cost_gbp).toFixed(2)}`} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Proceeds GBP" secondary={`£${parseFloat(data.proceeds_gbp).toFixed(2)}`} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Cost Basis GBP" secondary={`£${parseFloat(data.cost_basis_gbp).toFixed(2)}`} />
          </ListItem>
          <ListItem>
            <ListItemText primary="Gain GBP" secondary={`£${parseFloat(data.gain_gbp).toFixed(2)}`} />
          </ListItem>
          <ListItem>
            <ListItemText primary="CGT Due GBP" secondary={`£${parseFloat(data.cgt_due_gbp).toFixed(2)}`} />
          </ListItem>
        </List>
      </Box>

      {calc.equations && calc.equations.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1">Calculation Equations</Typography>
          <List dense>
            {calc.equations.map((eq: string, index: number) => (
              <ListItem key={index}>
                <ListItemText primary={`Step ${index + 1}`} secondary={eq} />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {data.details && data.details.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1">Calculation Details</Typography>
          {data.details.map((detail, index) => (
            <Box key={index} sx={{ mb: 2, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
              <Typography variant="subtitle2">{detail.explanation}</Typography>
              <Divider sx={{ my: 1 }} />
              <Box sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {detail.equations}
              </Box>
            </Box>
          ))}
        </Box>
      )}

      {numericTrace && Object.keys(numericTrace).length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1">Numeric Trace</Typography>
          <List dense>
            {Object.entries(numericTrace).map(([key, value]) => (
              <ListItem key={key}>
                <ListItemText
                  primary={key.replace(/_/g, ' ').toUpperCase()}
                  secondary={typeof value === 'string' ? value : JSON.stringify(value)}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {calc.inputs && (
        <Box>
          <Typography variant="subtitle1">Inputs</Typography>
          <pre style={{ backgroundColor: '#f5f5f5', padding: 8, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(calc.inputs, null, 2)}
          </pre>
        </Box>
      )}
    </Box>
  );
};

export default TraceModel;