/**
 * BatchUploadForm.js
 *
 * Collects PGN input via file upload or paste, validates game count,
 * and submits an array of PGN strings for batch analysis.
 *
 * Props:
 *   - onSubmit: function(pgnList)
 *   - isLoading: boolean
 *
 * Pure display/input component with local state only.
 */

import React, { useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Typography,
  TextField
} from '@mui/material';

const BatchUploadForm = ({ onSubmit, isLoading }) => {
  const fileInputRef = useRef(null);
  const [pgnText, setPgnText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [validationError, setValidationError] = useState(null);
  const [gameCount, setGameCount] = useState(0);

  const splitPgnGames = (text) => {
    if (!text || typeof text !== 'string') {
      return [];
    }

    const trimmedText = text.trim();
    if (!trimmedText) {
      return [];
    }

    const games = trimmedText
      .split(/(?=^\[Event\s)/m)
      .map((game) => game.trim())
      .filter(Boolean);

    return games;
  };

  const updateGameCount = (games) => {
    setGameCount(games.length);
    setValidationError(null);
  };

  const handleFileButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (event) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(files);

    if (files.length === 0) {
      setPgnText('');
      setGameCount(0);
      setValidationError(null);
      return;
    }

    try {
      const fileContents = await Promise.all(
        files.map((file) => file.text())
      );
      const combinedText = fileContents.join('\n\n');
      setPgnText(combinedText);
      updateGameCount(splitPgnGames(combinedText));
    } catch (error) {
      setValidationError('Unable to read one or more PGN files.');
      setGameCount(0);
    }
  };

  const handlePgnTextChange = (event) => {
    const value = event.target.value;
    setPgnText(value);
    setSelectedFiles([]);
    updateGameCount(splitPgnGames(value));
  };

  const handleSubmit = () => {
    const pgnList = splitPgnGames(pgnText);
    const count = pgnList.length;

    if (count < 5) {
      setValidationError('Batch analysis requires at least 5 games to detect patterns.');
      setGameCount(count);
      return;
    }

    if (count > 30) {
      setValidationError('Batch analysis supports a maximum of 30 games.');
      setGameCount(count);
      return;
    }

    setValidationError(null);
    onSubmit(pgnList);
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'grid', gap: 3 }}>
          <Box sx={{ display: 'grid', gap: 1.5 }}>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              Upload PGN Files
            </Typography>
            <Button
              variant="outlined"
              onClick={handleFileButtonClick}
              disabled={isLoading}
            >
              Choose PGN Files
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pgn"
              multiple
              hidden
              onChange={handleFileChange}
            />
            <Typography variant="body2" color="text.secondary">
              {selectedFiles.length > 0 ? `${selectedFiles.length} files selected` : 'No files selected'}
            </Typography>
          </Box>

          <Box sx={{ display: 'grid', gap: 1.5 }}>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              Or Paste PGN Text
            </Typography>
            <TextField
              multiline
              rows={8}
              fullWidth
              placeholder="Paste PGN text here..."
              value={pgnText}
              onChange={handlePgnTextChange}
              disabled={isLoading}
            />
          </Box>

          <Typography variant="body2" color="text.secondary">
            {gameCount} games detected
          </Typography>

          {validationError ? (
            <Alert severity="error">
              {validationError}
            </Alert>
          ) : null}

          <Button
            variant="contained"
            fullWidth
            onClick={handleSubmit}
            disabled={isLoading || gameCount === 0}
          >
            {isLoading ? <CircularProgress size={20} color="inherit" /> : 'Analyze Games'}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default BatchUploadForm;
