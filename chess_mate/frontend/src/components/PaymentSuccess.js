import React, { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { CheckCircle } from 'lucide-react';
import { UserContext } from '../contexts/UserContext';
import api from '../services/api';

const PaymentSuccess = () => {
  const navigate = useNavigate();
  const [isProcessing, setIsProcessing] = useState(true);
  const [retryCount, setRetryCount] = useState(0);
  const [sessionProcessed, setSessionProcessed] = useState(false);
  const { refreshUserData } = useContext(UserContext);
  const MAX_RETRIES = 3;

  useEffect(() => {
    const confirmPayment = async () => {
      try {
        const sessionId = new URLSearchParams(window.location.search).get('session_id');
        if (!sessionId) {
          throw new Error('No session ID found');
        }

        const accessToken = localStorage.getItem('tokens') ? JSON.parse(localStorage.getItem('tokens')).access : null;
        if (!accessToken) {
          throw new Error('No access token found');
        }

        const response = await api.post('/api/confirm-purchase/', 
          { session_id: sessionId },
          {
            headers: {
              'Authorization': `Bearer ${accessToken}`
            }
          }
        );

        if (response.data.credits) {
          await refreshUserData(); // Refresh user data to update credits
          setSessionProcessed(true);
          toast.success('Payment processed successfully!');
          setTimeout(() => navigate('/dashboard'), 3000);
        }
      } catch (error) {
        console.error('Payment confirmation error:', error);
        if (retryCount < MAX_RETRIES) {
          setRetryCount(prev => prev + 1);
          setTimeout(confirmPayment, 2000); // Retry after 2 seconds
        } else {
          toast.error('Failed to process payment. Please contact support.');
          setTimeout(() => navigate('/dashboard'), 3000);
        }
      } finally {
        setIsProcessing(false);
      }
    };

    if (!sessionProcessed) {
      confirmPayment();
    }
  }, [navigate, retryCount, sessionProcessed, refreshUserData]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <div className="text-center">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
            <h2 className="mt-4 text-2xl font-medium text-gray-900">
              {isProcessing ? 'Processing Payment...' : 'Payment Successful!'}
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              {isProcessing 
                ? retryCount > 0 
                  ? `Retrying confirmation... (Attempt ${retryCount} of ${MAX_RETRIES})`
                  : 'Please wait while we confirm your purchase.'
                : 'Thank you for your purchase. Your credits have been added to your account.'}
            </p>
            {!isProcessing && (
              <p className="mt-4 text-sm text-gray-500">
                Redirecting you back to the dashboard...
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaymentSuccess; 
