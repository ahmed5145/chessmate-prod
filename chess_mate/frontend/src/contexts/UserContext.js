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
        // Check different possible locations of the credits value
        if (profileData.data && profileData.data.profile && profileData.data.profile.credits !== undefined) {
          setCredits(profileData.data.profile.credits);
          console.log('Credits found in profileData.data.profile.credits:', profileData.data.profile.credits);
        } else if (profileData.data && profileData.data.credits !== undefined) {
          setCredits(profileData.data.credits);
          console.log('Credits found in profileData.data.credits:', profileData.data.credits);
        } else if (profileData.profile && profileData.profile.credits !== undefined) {
          setCredits(profileData.profile.credits);
          console.log('Credits found in profileData.profile.credits:', profileData.profile.credits);
        } else if (profileData.credits !== undefined) {
          setCredits(profileData.credits);
          console.log('Credits found in profileData.credits:', profileData.credits);
        } else {
          console.warn('No credits found in profile data. Data structure:', JSON.stringify(profileData, null, 2));
          // Default to 0 credits if none found
          setCredits(0);
        }
      } else {
        console.warn('No profile data returned from getUserProfile');
      }
    } catch (error) {
      console.error('Error refreshing user data:', error);
      if (error.response) {
        console.error('Response data:', error.response.data);
        console.error('Response status:', error.response.status);
      }
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
