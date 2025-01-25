import React, { createContext, useState, useEffect, useCallback, useContext } from 'react';

const UserContext = createContext();

export const UserProvider = ({ children }) => {
  const [credits, setCredits] = useState(0);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://3.133.97.72/api';

  const fetchCredits = useCallback(async () => {
    try {
      const accessToken = localStorage.getItem('tokens') ? JSON.parse(localStorage.getItem('tokens')).access : null;
      if (!accessToken) {
        console.error('No access token found');
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${API_BASE_URL}/credits/`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch credits');
      }
      
      const data = await response.json();
      if (typeof data.credits === 'number') {
        setCredits(data.credits);
      }
    } catch (error) {
      console.error('Error fetching credits:', error);
    } finally {
      setIsLoading(false);
    }
  }, [API_BASE_URL]);

  useEffect(() => {
    fetchCredits();
    // Set up periodic refresh every 30 seconds
    const refreshInterval = setInterval(fetchCredits, 30000);
    return () => clearInterval(refreshInterval);
  }, [fetchCredits]);

  const value = {
    credits,
    setCredits,
    user,
    setUser,
    isLoading,
    fetchCredits
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};

export { UserContext }; 
