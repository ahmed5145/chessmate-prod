/**
 * Opening matchup recommendation with bold opening name + ECO for scanability.
 */

import React from 'react';
import { Typography, Box } from '@mui/material';

const boldSpan = (text) => (
  <Box component="span" sx={{ fontWeight: 700 }}>
    {text}
  </Box>
);

const OpeningRecommendationText = ({ item }) => {
  const recommendation = item?.recommendation || '';
  const openingName = item?.opening_name;
  const ecoCode = item?.eco_code;

  if (!recommendation) {
    return null;
  }

  if (!openingName) {
    return <Typography variant="body2">{recommendation}</Typography>;
  }

  const ecoSuffix = ecoCode ? ` (${ecoCode})` : '';
  const boldLabel = `${openingName}${ecoSuffix}`;
  const fullIndex = recommendation.indexOf(boldLabel);

  if (fullIndex !== -1) {
    return (
      <Typography variant="body2">
        {recommendation.slice(0, fullIndex)}
        {boldSpan(boldLabel)}
        {recommendation.slice(fullIndex + boldLabel.length)}
      </Typography>
    );
  }

  const nameIndex = recommendation.indexOf(openingName);
  if (nameIndex !== -1) {
    const afterName = recommendation.slice(nameIndex + openingName.length);
    return (
      <Typography variant="body2">
        {recommendation.slice(0, nameIndex)}
        {boldSpan(openingName)}
        {ecoCode && afterName.startsWith(ecoSuffix) ? (
          <>
            {boldSpan(ecoSuffix)}
            {afterName.slice(ecoSuffix.length)}
          </>
        ) : (
          afterName
        )}
      </Typography>
    );
  }

  return <Typography variant="body2">{recommendation}</Typography>;
};

export default OpeningRecommendationText;
