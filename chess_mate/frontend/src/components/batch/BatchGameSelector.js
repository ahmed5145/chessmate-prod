import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Checkbox,
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography
} from '@mui/material';
import { fetchUserGames } from '../../services/apiRequests';
import { formatGamePlatformLabel } from '../../utils/gamePlatform';

const timeControlOptions = [
  { value: 'all', label: 'All Time Controls' },
  { value: 'bullet', label: 'Bullet' },
  { value: 'blitz', label: 'Blitz' },
  { value: 'rapid', label: 'Rapid' },
  { value: 'classical', label: 'Classical' },
];

const normalizeTimeControl = (game) => String(game?.time_control || game?.time_control_type || '').toLowerCase();

const BatchGameSelector = ({ onSubmit, isLoading }) => {
  const [availableGames, setAvailableGames] = useState([]);
  const [selectedGameIds, setSelectedGameIds] = useState([]);
  const [timeControlFilter, setTimeControlFilter] = useState('all');
  const [loadingGames, setLoadingGames] = useState(true);
  const [error, setError] = useState(null);
  const [validationError, setValidationError] = useState(null);

  useEffect(() => {
    let mounted = true;

    const loadGames = async () => {
      setLoadingGames(true);
      setError(null);

      try {
        const response = await fetchUserGames();
        const games = Array.isArray(response)
          ? response
          : Array.isArray(response?.results)
            ? response.results
            : [];

        if (mounted) {
          setAvailableGames(games);
        }
      } catch (loadError) {
        if (mounted) {
          setError(loadError?.message || 'Failed to load saved games.');
        }
      } finally {
        if (mounted) {
          setLoadingGames(false);
        }
      }
    };

    loadGames();

    return () => {
      mounted = false;
    };
  }, []);

  const filteredGames = useMemo(() => {
    return (Array.isArray(availableGames) ? availableGames : []).filter((game) => {
      if (timeControlFilter === 'all') {
        return true;
      }

      return normalizeTimeControl(game) === timeControlFilter;
    });
  }, [availableGames, timeControlFilter]);

  useEffect(() => {
    const availableIds = new Set(filteredGames.map((game) => Number(game.id)));
    setSelectedGameIds((previousIds) => previousIds.filter((id) => availableIds.has(id)));
  }, [filteredGames]);

  useEffect(() => {
    if (selectedGameIds.length < 5 || selectedGameIds.length > 30) {
      setValidationError('Select between 5 and 30 games to analyze.');
      return;
    }

    setValidationError(null);
  }, [selectedGameIds]);

  const toggleGame = (gameId) => {
    const numericGameId = Number(gameId);

    setSelectedGameIds((previousIds) => {
      if (previousIds.includes(numericGameId)) {
        return previousIds.filter((id) => id !== numericGameId);
      }

      if (previousIds.length >= 30) {
        return previousIds;
      }

      return [...previousIds, numericGameId];
    });
  };

  const toggleAllVisible = () => {
    if (filteredGames.length === 0) {
      return;
    }

    const visibleIds = filteredGames.map((game) => Number(game.id));
    const allSelected = visibleIds.every((id) => selectedGameIds.includes(id));

    if (allSelected) {
      setSelectedGameIds((previousIds) => previousIds.filter((id) => !visibleIds.includes(id)));
      return;
    }

    setSelectedGameIds((previousIds) => {
      const merged = new Set(previousIds);
      visibleIds.forEach((id) => merged.add(id));
      return Array.from(merged).slice(0, 30);
    });
  };

  const handleSubmit = () => {
    if (selectedGameIds.length < 5 || selectedGameIds.length > 30) {
      setValidationError('Select between 5 and 30 games to analyze.');
      return;
    }

    setValidationError(null);
    onSubmit(selectedGameIds);
  };

  const formatResult = (result) => {
    const normalized = String(result || '').toLowerCase();

    if (normalized === 'win') {
      return 'W';
    }

    if (normalized === 'loss') {
      return 'L';
    }

    if (normalized === 'draw') {
      return 'D';
    }

    return normalized ? normalized.toUpperCase() : '?';
  };

  const gameCountLabel = `${filteredGames.length} games available, ${selectedGameIds.length} selected`;
  const isSelectionValid = selectedGameIds.length >= 5 && selectedGameIds.length <= 30;

  if (!loadingGames && !error && (Array.isArray(availableGames) ? availableGames.length : 0) === 0) {
    return (
      <Alert severity="info">
        No games found. Import games from your chess.com or lichess account first.
      </Alert>
    );
  }

  return (
    <Box sx={{ display: 'grid', gap: 2 }}>
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'stretch', sm: 'center' }}>
        <FormControl fullWidth size="small">
          <InputLabel id="time-control-filter-label">Time Control</InputLabel>
          <Select
            labelId="time-control-filter-label"
            value={timeControlFilter}
            label="Time Control"
            onChange={(event) => setTimeControlFilter(event.target.value)}
          >
            {timeControlOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button variant="outlined" onClick={toggleAllVisible} disabled={loadingGames || filteredGames.length === 0}>
          Select/Deselect All
        </Button>
      </Stack>

      <Typography variant="body2" color="text.secondary">
        {gameCountLabel}
      </Typography>

      {loadingGames ? (
        <Typography variant="body2" color="text.secondary">
          Loading saved games...
        </Typography>
      ) : (
        <Paper variant="outlined" sx={{ maxHeight: 420, overflow: 'auto' }}>
          <List disablePadding>
            {filteredGames.map((game) => {
              const gameId = Number(game.id);
              const checked = selectedGameIds.includes(gameId);
              const result = String(game.result || '').toLowerCase();
              const resultColor = result === 'win' ? 'success' : result === 'loss' ? 'error' : 'default';

              return (
                <ListItem key={gameId} disablePadding divider>
                  <ListItemButton onClick={() => toggleGame(gameId)}>
                    <ListItemIcon>
                      <Checkbox edge="start" checked={checked} tabIndex={-1} disableRipple />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                          <Typography variant="body2" fontWeight={600}>
                            {game.opponent || `${game.white || 'White'} vs ${game.black || 'Black'}`}
                          </Typography>
                          <Chip size="small" label={formatResult(game.result)} color={resultColor} />
                          <Chip
                            size="small"
                            variant="outlined"
                            label={String(game.time_control || game.time_control_type || 'unknown').toUpperCase()}
                          />
                          {formatGamePlatformLabel(game.platform) ? (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={formatGamePlatformLabel(game.platform)}
                            />
                          ) : null}
                        </Stack>
                      }
                      secondary={
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
                          <Typography variant="caption" color="text.secondary">
                            {game.opening_name || 'Unknown Opening'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {game.date_played ? new Date(game.date_played).toLocaleDateString() : 'Unknown date'}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </Paper>
      )}

      {validationError ? <Alert severity="error">{validationError}</Alert> : null}

      <Button variant="contained" onClick={handleSubmit} disabled={isLoading || !isSelectionValid}>
        Analyze {selectedGameIds.length} Games
      </Button>
    </Box>
  );
};

export default BatchGameSelector;
