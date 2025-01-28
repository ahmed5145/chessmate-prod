import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { analyzeSpecificGame, checkAnalysisStatus } from '../services/gameAnalysisService';
import GameFeedback from './GameFeedback';
import LoadingSpinner from './LoadingSpinner';

const SingleGameAnalysis = () => {
    const { gameId } = useParams();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [analysisData, setAnalysisData] = useState(null);
    const [taskId, setTaskId] = useState(null);
    const [pollingInterval, setPollingInterval] = useState(null);

    const startPolling = useCallback((taskId) => {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }

        const interval = setInterval(async () => {
            try {
                console.log('Checking analysis status...');
                const response = await checkAnalysisStatus(taskId);
                console.log('Status response:', response);

                if (response.status === 'completed') {
                    clearInterval(interval);
                    setPollingInterval(null);
                    setLoading(false);
                    setAnalysisData(response.result);
                } else if (response.status === 'failed') {
                    clearInterval(interval);
                    setPollingInterval(null);
                    setLoading(false);
                    setError(response.error || 'Analysis failed');
                }
                // Continue polling if status is 'in_progress'
            } catch (err) {
                console.error('Error checking status:', err);
                clearInterval(interval);
                setPollingInterval(null);
                setLoading(false);
                setError(err.message || 'Failed to check analysis status');
            }
        }, 2000); // Poll every 2 seconds

        setPollingInterval(interval);
    }, []);

    const startAnalysis = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            console.log('Starting analysis for game:', gameId);

            const response = await analyzeSpecificGame(gameId);
            console.log('Analysis response:', response);

            if (response.status === 'started' && response.task_id) {
                setTaskId(response.task_id);
                startPolling(response.task_id);
            } else {
                setLoading(false);
                setError('Failed to start analysis');
            }
        } catch (err) {
            console.error('Error starting analysis:', err);
            setLoading(false);
            setError(err.message || 'Failed to start analysis');
        }
    }, [gameId, startPolling]);

    useEffect(() => {
        startAnalysis();

        return () => {
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
        };
    }, [startAnalysis, pollingInterval]);

    if (error) {
        return (
            <div className="error-container">
                <h2>Error</h2>
                <p>{error}</p>
                <button onClick={startAnalysis}>Retry Analysis</button>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="loading-container">
                <LoadingSpinner />
                <p>Analyzing game... This may take a few minutes.</p>
            </div>
        );
    }

    return (
        <div className="analysis-container">
            {analysisData ? (
                <GameFeedback feedback={analysisData} />
            ) : (
                <p>No analysis data available</p>
            )}
        </div>
    );
};

export default SingleGameAnalysis; 