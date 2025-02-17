import React from 'react';
import { Navigate } from 'react-router-dom';
import PropTypes from 'prop-types';
import { jwtDecode } from "jwt-decode";

const ProtectedRoute = ({ children }) => {
  const tokens = localStorage.getItem('tokens');
  
  // Check if tokens exist
  if (!tokens) {
    return <Navigate to="/login" replace />;
  }

  try {
    // Parse and validate tokens
    const { access } = JSON.parse(tokens);
    const decoded = jwtDecode(access);
    const currentTime = Date.now() / 1000;
    
    // If token is expired, clear it and redirect
    if (decoded.exp < currentTime) {
      localStorage.removeItem('tokens');
      return <Navigate to="/login" replace />;
    }
    
    return children;
  } catch (error) {
    // If there's any error parsing/validating tokens, clear them and redirect
    console.error('Token validation error:', error);
    localStorage.removeItem('tokens');
    return <Navigate to="/login" replace />;
  }
};

ProtectedRoute.propTypes = {
  children: PropTypes.node.isRequired,
};

export default ProtectedRoute; 