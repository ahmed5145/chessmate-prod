import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

const AnalyzeGameConfirmDialog = ({
  open,
  onClose,
  onConfirm,
  creditsRequired = 1,
  creditsAvailable = 0,
  isReanalyze = false,
  firstReviewFree = false,
  fromBatch = false,
  confirming = false,
}) => {
  const { isDarkMode } = useTheme();

  if (!open) {
    return null;
  }

  const effectiveCost = isReanalyze
    ? creditsRequired
    : (fromBatch ? 0 : (firstReviewFree ? 0 : creditsRequired));
  const hasEnoughCredits = Number(creditsAvailable) >= effectiveCost;

  const costLabel = effectiveCost === 0
    ? (fromBatch ? 'Free from batch citation' : 'First review free')
    : `${effectiveCost} credit${effectiveCost === 1 ? '' : 's'}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="analyze-confirm-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div
        className={`relative w-full max-w-md rounded-xl shadow-xl border p-6 ${
          isDarkMode ? 'bg-gray-800 border-gray-700 text-white' : 'bg-white border-gray-200 text-gray-900'
        }`}
      >
        <h2 id="analyze-confirm-title" className="text-lg font-semibold">
          {isReanalyze ? 'Re-run deep review?' : 'Run deep game review?'}
        </h2>
        <p className={`mt-2 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Optional depth-20 coach review for this game — separate from Batch Coach, which is included
          after import.
        </p>
        {firstReviewFree && !isReanalyze && !fromBatch ? (
          <p className={`mt-3 text-sm font-medium ${isDarkMode ? 'text-emerald-300' : 'text-emerald-700'}`}>
            Your first depth-20 single-game review is free — no credit needed.
          </p>
        ) : null}
        <ul className={`mt-4 space-y-2 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          <li>
            <strong>Cost:</strong> {costLabel}
          </li>
          <li>
            <strong>Your balance:</strong> {creditsAvailable} credit{Number(creditsAvailable) === 1 ? '' : 's'}
          </li>
          <li>Engine depth 20 · coach-style feedback · move-by-move breakdown</li>
          <li>Runs in the background — you can leave and check Games when ready</li>
        </ul>

        {!hasEnoughCredits ? (
          <p className={`mt-4 text-sm ${isDarkMode ? 'text-amber-300' : 'text-amber-700'}`}>
            You need {effectiveCost} credit{effectiveCost === 1 ? '' : 's'} to analyze this game.{' '}
            <Link to="/credits" className="underline font-medium" onClick={onClose}>
              Get credits
            </Link>
          </p>
        ) : null}

        <div className="mt-6 flex flex-col-reverse sm:flex-row gap-2 sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={confirming}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              isDarkMode
                ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!hasEnoughCredits || confirming}
            className={`px-4 py-2 rounded-lg text-sm font-medium text-white ${
              hasEnoughCredits && !confirming
                ? 'bg-indigo-600 hover:bg-indigo-700'
                : 'bg-indigo-400 cursor-not-allowed'
            }`}
          >
            {confirming
              ? 'Starting…'
              : isReanalyze
                ? 'Re-analyze (1 credit)'
                : effectiveCost === 0
                  ? 'Start free review'
                  : `Analyze (${effectiveCost} credit${effectiveCost === 1 ? '' : 's'})`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalyzeGameConfirmDialog;
