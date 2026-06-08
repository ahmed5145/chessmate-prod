import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const EngineMetaNote = ({ engineMeta = null, batchContext = null }) => {
  const { isDarkMode } = useTheme();
  const note =
    engineMeta?.classification_note
    || batchContext?.classification_disclaimer
    || null;

  if (!note) {
    return null;
  }

  return (
    <p className={`mb-4 text-xs ${isDarkMode ? 'text-gray-500' : 'text-gray-500'}`}>
      {note}
    </p>
  );
};

export default EngineMetaNote;
