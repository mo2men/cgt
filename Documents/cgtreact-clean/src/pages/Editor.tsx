import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Typography, Button, Box } from '@mui/material';
import EditorForm from '../components/EditorForm';

const Editor = () => {
  const navigate = useNavigate();

  return (
    <>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Transaction Editor</Typography>
        <Button variant="outlined" onClick={() => navigate('/')}>
          Back to Dashboard
        </Button>
      </Box>
      <EditorForm />
    </>
  );
};

export default Editor;