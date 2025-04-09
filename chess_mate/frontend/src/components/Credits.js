import React, { useState, useEffect, useContext } from 'react';
import { toast } from 'react-hot-toast';
import { CreditCard } from 'lucide-react';
import { UserContext } from '../contexts/UserContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

const Credits = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { credits, fetchUserData } = useContext(UserContext);
  const { isDarkMode } = useTheme();

  useEffect(() => {
    fetchUserData();
  }, [fetchUserData]);

  const handlePurchase = async (packageId) => {
    setLoading(true);
    try {
      const accessToken = localStorage.getItem('tokens') ? JSON.parse(localStorage.getItem('tokens')).access : null;
      if (!accessToken) {
        toast.error('Please log in to purchase credits');
        return;
      }

      const response = await api.post('/api/purchase-credits/', {
        package_id: packageId
      }, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });

      if (!response.data.checkout_url) {
        throw new Error('No checkout URL received');
      }

      window.location.href = response.data.checkout_url;
    } catch (error) {
      console.error('Error processing request:', error);
      toast.error(error.message || 'Failed to process request');
    } finally {
      setLoading(false);
    }
  };

  const creditPackages = [
    {
      id: 'basic',
      name: 'Basic Package',
      credits: 100,
      price: 9.99,
      description: 'Perfect for casual players',
      features: [
        '100 game analyses',
        'Basic feedback',
        'Opening suggestions',
        'Valid for 3 months'
      ]
    },
    {
      id: 'pro',
      name: 'Pro Package',
      credits: 300,
      price: 24.99,
      description: 'Great for regular analysis',
      popular: true,
      features: [
        '300 game analyses',
        'Detailed feedback',
        'Opening & middlegame suggestions',
        'Valid for 6 months'
      ]
    },
    {
      id: 'premium',
      name: 'Premium Package',
      credits: 1000,
      price: 79.99,
      description: 'Best value for serious players',
      features: [
        '1000 game analyses',
        'Advanced feedback',
        'Complete game analysis',
        'Valid for 12 months'
      ]
    }
  ];

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
      <div className="sm:flex sm:flex-col sm:align-center">
        <h2 className={`text-3xl font-extrabold ${isDarkMode ? 'text-white' : 'text-gray-900'} sm:text-center`}>
          Purchase Analysis Credits
        </h2>
        <p className={`mt-5 text-xl ${isDarkMode ? 'text-gray-300' : 'text-gray-500'} sm:text-center`}>
          Get credits to analyze your chess games and receive detailed feedback
        </p>
        <div className="mt-4 text-center">
          <span className={`inline-flex items-center px-4 py-2 rounded-md ${
            isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-50 text-indigo-700'
          }`}>
            <CreditCard className="h-5 w-5 mr-2" />
            You currently have {credits} credits available
          </span>
        </div>
      </div>

      <div className="mt-12 space-y-4 sm:mt-16 sm:space-y-0 sm:grid sm:grid-cols-2 sm:gap-6 lg:max-w-4xl lg:mx-auto xl:max-w-none xl:mx-0 xl:grid-cols-3">
        {creditPackages.map((pkg) => (
          <div
            key={pkg.id}
            className={`rounded-lg shadow-sm divide-y ${
              isDarkMode
                ? 'bg-gray-800 divide-gray-700'
                : 'divide-gray-200 bg-white'
            } ${
              pkg.popular
                ? 'border-2 border-indigo-500 relative'
                : isDarkMode
                  ? 'border border-gray-700'
                  : 'border border-gray-200'
            }`}
          >
            {pkg.popular && (
              <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2">
                <span className={`inline-flex rounded-full px-4 py-1 text-xs font-semibold ${
                  isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-100 text-indigo-600'
                }`}>
                  Most Popular
                </span>
              </div>
            )}
            <div className="p-6">
              <h3 className={`text-lg leading-6 font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                {pkg.name}
              </h3>
              <p className={`mt-4 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                {pkg.description}
              </p>
              <p className="mt-8">
                <span className={`text-4xl font-extrabold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  ${pkg.price}
                </span>
              </p>
              <p className={`mt-2 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                for {pkg.credits} credits
              </p>
              <button
                onClick={() => handlePurchase(pkg.id)}
                disabled={loading}
                className={`mt-8 block w-full text-white font-medium py-2 px-4 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ${
                  pkg.popular
                    ? isDarkMode
                      ? 'bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500'
                      : 'bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500'
                    : isDarkMode
                      ? 'bg-gray-600 hover:bg-gray-700 focus:ring-gray-500'
                      : 'bg-gray-600 hover:bg-gray-700 focus:ring-gray-500'
                } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {loading ? 'Processing...' : 'Purchase Credits'}
              </button>
            </div>
            <div className="px-6 pt-6 pb-8">
              <h4 className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                What's included
              </h4>
              <ul className="mt-6 space-y-4">
                {pkg.features.map((feature, index) => (
                  <li key={index} className="flex space-x-3">
                    <svg
                      className={`flex-shrink-0 h-5 w-5 ${isDarkMode ? 'text-green-400' : 'text-green-500'}`}
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Credits;
