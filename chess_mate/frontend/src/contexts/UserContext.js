import React, { createContext, useState, useEffect, useCallback, useContext } from 'react';
import { getUserProfile } from '../services/apiRequests';
import api from '../services/api';

const UserContext = createContext();

export const UserProvider = ({ children }) => {
  const [credits, setCredits] = useState(0);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUserData = useCallback(async () => {
    try {
      const tokens = localStorage.getItem('tokens');
      if (!tokens) {
        setIsLoading(false);
        return;
      }

      // Set authorization header
      const { access } = JSON.parse(tokens);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

      // Fetch profile data
      const profileData = await getUserProfile();
      if (profileData) {
        setUser(profileData);
        setCredits(profileData.credits);
      }
    } catch (error) {
      console.error('Error fetching user data:', error);
      // If unauthorized, clear tokens
      if (error.response?.status === 401) {
        localStorage.removeItem('tokens');
        delete api.defaults.headers.common['Authorization'];
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Refresh user data function
  const refreshUserData = useCallback(async () => {
    try {
      const tokens = localStorage.getItem('tokens');
      if (!tokens) return;

      const { access } = JSON.parse(tokens);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;

      const profileData = await getUserProfile();
      if (profileData) {
        setUser(profileData);
        setCredits(profileData.credits);
      }
    } catch (error) {
      console.error('Error refreshing user data:', error);
    }
  }, []);

  // Fetch user data when the component mounts and when tokens change
  useEffect(() => {
    fetchUserData();
  }, [fetchUserData]);

  const value = {
    credits,
    setCredits,
    user,
    setUser,
    isLoading,
    fetchUserData,
    refreshUserData
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
