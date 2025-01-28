import React, { createContext, useState, useEffect, useCallback, useContext } from 'react';
import { getUserProfile } from '../services/apiRequests';

const UserContext = createContext();

export const UserProvider = ({ children }) => {
  const [credits, setCredits] = useState(0);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCredits = useCallback(async () => {
    try {
      const tokens = localStorage.getItem('tokens');
      if (!tokens) {
        setIsLoading(false);
        return;
      }

      const profileData = await getUserProfile();
      if (profileData && typeof profileData.credits === 'number') {
        setCredits(profileData.credits);
        setUser(profileData);
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch credits when the component mounts and when tokens change
  useEffect(() => {
    fetchCredits();
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
