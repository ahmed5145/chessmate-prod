/**
 * BatchUpload.js
 *
 * Batch upload page that collects PGN input and creates a new batch analysis.
 *
 * Pure page component with local loading/error state only.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Container,
  Typography
} from '@mui/material';
import BatchGameSelector from './BatchGameSelector';
import { createBatch } from '../../services/apiRequests';

const BatchUpload = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (selectedGameIds) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await createBatch({ gameIds: selectedGameIds });
      navigate(`/batch-report/${response.batch_id}`);
    } catch (submitError) {
      const message = submitError?.message || submitError?.detail || 'Failed to start batch analysis.';
      setError(message);
      setIsLoading(false);
    }
  };

  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Box sx={{ display: 'grid', gap: 3 }}>
        <Typography variant="h4" align="center" sx={{ fontWeight: 700 }}>
          Batch Game Analysis
        </Typography>

        {error ? (
          <Alert severity="error">
            {error}
          </Alert>
        ) : null}

        <BatchGameSelector onSubmit={handleSubmit} isLoading={isLoading} />
      </Box>
    </Container>
  );
};

export default BatchUpload;
