/**
 * Styled outbound link to Lichess study / puzzles / endgames.
 */

import React from 'react';
import { Button } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import SportsEsportsIcon from '@mui/icons-material/SportsEsports';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import FlagIcon from '@mui/icons-material/Flag';

const KIND_META = {
  puzzle: { icon: SportsEsportsIcon, color: 'primary', defaultLabel: 'Train on Lichess' },
  opening: { icon: MenuBookIcon, color: 'secondary', defaultLabel: 'Study on Lichess' },
  endgame: { icon: FlagIcon, color: 'warning', defaultLabel: 'Practice on Lichess' },
};

const LichessActionButton = ({ label, url, kind = 'puzzle', size = 'small', onClick }) => {
  if (!url) {
    return null;
  }

  const meta = KIND_META[kind] || KIND_META.puzzle;
  const Icon = meta.icon;

  return (
    <Button
      size={size}
      variant="outlined"
      color={meta.color}
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={onClick}
      startIcon={<Icon fontSize="small" />}
      endIcon={<OpenInNewIcon fontSize="small" />}
      sx={{
        textTransform: 'none',
        fontWeight: 600,
        borderWidth: 1.5,
        '&:hover': {
          borderWidth: 1.5,
        },
      }}
    >
      {label || meta.defaultLabel}
    </Button>
  );
};

export default LichessActionButton;
