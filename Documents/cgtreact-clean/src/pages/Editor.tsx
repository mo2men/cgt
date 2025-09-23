import React from 'react';
import { Typography } from '@mui/material';
import EditorForm from '../components/EditorForm';

const Editor = () => (
  <>
    <Typography variant="h4" gutterBottom>Transaction Editor</Typography>
    <EditorForm />
  </>
);

export default Editor;