import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LogOut,
  Menu,
  X,
  Sun,
  Moon,
  Home,
  LayoutDashboard,
  Crown,
  LineChart,
  User,
  LogIn,
  UserPlus,
  BarChart,
  Coins
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import { logoutUser, fetchProfileData } from '../services/apiRequests';

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { credits, setCredits, refreshUserData } = useUser();
  const { isDarkMode, toggleDarkMode } = useTheme();
  const isLoggedIn = !!localStorage.getItem('tokens');

  // Refresh user data on mount and when location changes
  useEffect(() => {
    if (isLoggedIn) {
      refreshUserData();
    }
  }, [isLoggedIn, location.pathname]);

  const handleLogout = async () => {
    try {
      const success = await logoutUser();
      if (success) {
        setCredits(0);
        toast.success('Logged out successfully');
      }
      // Always navigate to login page, even if server request fails
      navigate('/login', { replace: true });
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Error during logout');
      // Still navigate to login page
      navigate('/login', { replace: true });
    }
  };

  const navLinks = isLoggedIn ? [
    { to: '/dashboard', icon: <LayoutDashboard size={20} />, text: 'Dashboard' },
    { to: '/games', icon: <Crown size={20} />, text: 'Games' },
    { to: '/batch-analysis', icon: <BarChart size={20} />, text: 'Batch Analysis' },
    { to: '/profile', icon: <User size={20} />, text: 'Profile' },
  ] : [
    { to: '/login', icon: <LogIn size={20} />, text: 'Login' },
    { to: '/register', icon: <UserPlus size={20} />, text: 'Sign Up', highlight: true },
  ];

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-200
      ${isDarkMode
        ? 'bg-gray-900 border-b border-gray-800'
        : 'bg-white border-b border-gray-200'}`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link
              to={isLoggedIn ? "/dashboard" : "/"}
              className={`flex items-center space-x-2 text-xl font-bold ${
                isDarkMode ? 'text-white hover:text-primary-300' : 'text-gray-900 hover:text-primary-600'
              } transition-colors duration-200`}
            >
              <Crown size={28} className="text-indigo-600" />
              <span>ChessMate</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden sm:flex sm:items-center sm:space-x-4">
            {isLoggedIn && (
              <Link
                to="/credits"
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors duration-200 cursor-pointer
                  ${isDarkMode ? 'bg-gray-800 hover:bg-gray-700' : 'bg-gray-100 hover:bg-gray-200'}`}
              >
                <Coins size={20} className={isDarkMode ? 'text-yellow-500' : 'text-yellow-600'} />
                <span className={`font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                  {credits}
                </span>
              </Link>
            )}

            {navLinks.map(({ to, icon, text, highlight }) => (
              <Link
                key={to}
                to={to}
                className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors duration-200 whitespace-nowrap
                  ${location.pathname === to
                    ? isDarkMode
                      ? 'bg-gray-800 text-white'
                      : 'bg-indigo-50 text-indigo-600'
                    : isDarkMode
                      ? 'text-gray-300 hover:bg-gray-800 hover:text-white'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-indigo-600'
                  }`}
              >
                {icon}
                <span>{text}</span>
              </Link>
            ))}

            {isLoggedIn && (
              <button
                onClick={handleLogout}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors duration-200
                  ${isDarkMode
                    ? 'bg-gray-800 text-white hover:bg-gray-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
              >
                <LogOut size={20} />
                <span>Logout</span>
              </button>
            )}

            <button
              onClick={toggleDarkMode}
              className={`inline-flex items-center justify-center p-2 rounded-lg transition-colors duration-200 h-10 w-10
                ${isDarkMode
                  ? 'bg-gray-800 text-white hover:bg-gray-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center sm:hidden">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className={`p-2 rounded-lg transition-colors duration-200
                ${isDarkMode
                  ? 'text-gray-300 hover:bg-gray-800'
                  : 'text-gray-600 hover:bg-gray-100'
                }`}
            >
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isOpen && (
        <div className={`sm:hidden ${isDarkMode ? 'bg-gray-900' : 'bg-white'} border-t ${isDarkMode ? 'border-gray-800' : 'border-gray-200'}`}>
          <div className="px-2 pt-2 pb-3 space-y-1">
            {isLoggedIn && (
              <Link
                to="/credits"
                onClick={() => setIsOpen(false)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors duration-200 cursor-pointer
                  ${isDarkMode ? 'bg-gray-800 hover:bg-gray-700' : 'bg-gray-100 hover:bg-gray-200'}`}
              >
                <Coins size={20} className={isDarkMode ? 'text-yellow-500' : 'text-yellow-600'} />
                <span className={`font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                  {credits}
                </span>
              </Link>
            )}

            {navLinks.map(({ to, icon, text }) => (
              <Link
                key={to}
                to={to}
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors duration-200
                  ${location.pathname === to
                    ? isDarkMode
                      ? 'bg-gray-800 text-white'
                      : 'bg-indigo-50 text-indigo-600'
                    : isDarkMode
                      ? 'text-gray-300 hover:bg-gray-800 hover:text-white'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-indigo-600'
                  }`}
                onClick={() => setIsOpen(false)}
              >
                {icon}
                <span>{text}</span>
              </Link>
            ))}

            {isLoggedIn && (
              <button
                onClick={() => {
                  handleLogout();
                  setIsOpen(false);
                }}
                className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors duration-200
                  ${isDarkMode
                    ? 'bg-gray-800 text-white hover:bg-gray-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
              >
                <LogOut size={20} />
                <span>Logout</span>
              </button>
            )}

            <button
              onClick={() => {
                toggleDarkMode();
                setIsOpen(false);
              }}
              className={`w-full flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors duration-200
                ${isDarkMode
                  ? 'bg-gray-800 text-white hover:bg-gray-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              <span>{isDarkMode ? 'Light Mode' : 'Dark Mode'}</span>
              {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
