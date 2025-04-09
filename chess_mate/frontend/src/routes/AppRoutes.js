import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from '../components/Dashboard';
import Profile from '../components/Profile';
import Login from '../components/Login';
import Register from '../components/Register';
import ForgotPassword from '../components/ForgotPassword';
import ResetPassword from '../components/ResetPassword';
import ResetPasswordSuccess from '../components/ResetPasswordSuccess';
import ResetPasswordFailed from '../components/ResetPasswordFailed';
import Credits from '../components/Credits';
import Games from '../components/Games';
import SingleGameAnalysis from '../components/SingleGameAnalysis';
import BatchAnalysis from '../components/BatchAnalysis';
import BatchAnalysisResults from '../components/BatchAnalysisResults';
import FetchGames from '../components/FetchGames';
import PaymentSuccess from '../components/PaymentSuccess';
import PaymentCancel from '../components/PaymentCancel';
import LandingPage from '../components/LandingPage';
import ProtectedRoute from './ProtectedRoute';

const AppRoutes = () => {
  const isAuthenticated = !!localStorage.getItem('tokens');

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/"
        element={<LandingPage />}
      />
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />}
      />
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Register />}
      />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/reset-password-success" element={<ResetPasswordSuccess />} />
      <Route path="/reset-password-failed" element={<ResetPasswordFailed />} />

      {/* Protected routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/credits"
        element={
          <ProtectedRoute>
            <Credits />
          </ProtectedRoute>
        }
      />
      <Route
        path="/games"
        element={
          <ProtectedRoute>
            <Games />
          </ProtectedRoute>
        }
      />
      <Route
        path="/game/:gameId/analysis"
        element={
          <ProtectedRoute>
            <SingleGameAnalysis />
          </ProtectedRoute>
        }
      />
      <Route
        path="/batch-analysis"
        element={
          <ProtectedRoute>
            <BatchAnalysis />
          </ProtectedRoute>
        }
      />
      <Route
        path="/batch-analysis/results/:taskId"
        element={
          <ProtectedRoute>
            <BatchAnalysisResults />
          </ProtectedRoute>
        }
      />
      <Route
        path="/fetch-games"
        element={
          <ProtectedRoute>
            <FetchGames />
          </ProtectedRoute>
        }
      />
      <Route
        path="/payment/success"
        element={
          <ProtectedRoute>
            <PaymentSuccess />
          </ProtectedRoute>
        }
      />
      <Route
        path="/payment/cancel"
        element={
          <ProtectedRoute>
            <PaymentCancel />
          </ProtectedRoute>
        }
      />

      {/* Catch all route */}
      <Route path="*" element={<Navigate to={isAuthenticated ? "/dashboard" : "/"} replace />} />
    </Routes>
  );
};

export default AppRoutes;
