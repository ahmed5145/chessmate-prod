import React from 'react';
import { Link } from 'react-router-dom';
import { Crown, Shield, Zap, Trophy, FileInput, Brain, Target, Star } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';

const Feature = ({ icon: Icon, title, description, delay = 0 }) => {
  const { isDarkMode } = useTheme();

  return (
    <div
      className={`p-6 rounded-xl ${
        isDarkMode ? 'bg-gray-800 hover:bg-gray-700' : 'bg-white hover:bg-gray-50'
      } transition-all duration-300 shadow-lg hover:shadow-xl hover:-translate-y-1 animate-fade-in`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`flex items-center justify-center w-14 h-14 mb-6 rounded-xl ${
        isDarkMode ? 'bg-indigo-900/50' : 'bg-indigo-50'
      } transform transition-transform duration-300 group-hover:scale-110`}>
        <Icon className={`w-7 h-7 ${
          isDarkMode ? 'text-indigo-300' : 'text-indigo-600'
        }`} />
      </div>
      <h3 className={`mb-3 text-xl font-bold ${
        isDarkMode ? 'text-white' : 'text-gray-900'
      }`}>{title}</h3>
      <p className={`${
        isDarkMode ? 'text-gray-300' : 'text-gray-600'
      } leading-relaxed`}>{description}</p>
    </div>
  );
};

const Testimonial = ({ quote, author, role, delay = 0 }) => {
  const { isDarkMode } = useTheme();

  return (
    <div
      className={`p-6 rounded-xl ${
        isDarkMode ? 'bg-gray-800' : 'bg-white'
      } shadow-lg animate-fade-in`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center mb-4">
        <Star className={`w-5 h-5 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-500'}`} />
        <Star className={`w-5 h-5 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-500'}`} />
        <Star className={`w-5 h-5 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-500'}`} />
        <Star className={`w-5 h-5 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-500'}`} />
        <Star className={`w-5 h-5 ${isDarkMode ? 'text-yellow-400' : 'text-yellow-500'}`} />
      </div>
      <p className={`mb-4 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'} italic`}>"{quote}"</p>
      <div>
        <p className={`font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{author}</p>
        <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>{role}</p>
      </div>
    </div>
  );
};

const LandingPage = () => {
  const { isDarkMode } = useTheme();
  const { user } = useUser();

  const features = [
    {
      icon: Brain,
      title: 'AI-Powered Analysis',
      description: 'Get deep insights into your games with our advanced chess engine and AI feedback system.',
    },
    {
      icon: Zap,
      title: 'Batch Processing',
      description: 'Save time by analyzing multiple games simultaneously and identifying patterns in your play.',
    },
    {
      icon: Target,
      title: 'Performance Tracking',
      description: 'Monitor your progress with detailed statistics, ratings tracking, and improvement metrics.',
    },
    {
      icon: FileInput,
      title: 'Platform Integration',
      description: 'Seamlessly import games from Chess.com, Lichess, and other major chess platforms.',
    },
  ];

  const testimonials = [
    {
      quote: "ChessMate has revolutionized my training routine. The AI insights are incredibly valuable.",
      author: "Magnus A.",
      role: "FIDE Master"
    },
    {
      quote: "The batch analysis feature saves me hours of work. Absolutely essential for serious players.",
      author: "Sarah L.",
      role: "Chess Coach"
    },
    {
      quote: "Finally, a chess analysis tool that's both powerful and easy to use. Highly recommended!",
      author: "David R.",
      role: "Club Player"
    }
  ];

  return (
    <div className={`min-h-screen ${
      isDarkMode ? 'bg-gray-900' : 'bg-gray-50'
    }`}>
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 z-0">
          <div className={`absolute inset-0 ${
            isDarkMode
              ? 'bg-gradient-to-br from-gray-900 via-indigo-900/20 to-gray-900'
              : 'bg-gradient-to-br from-gray-50 via-indigo-50/20 to-gray-50'
          }`}></div>
          <div className="absolute inset-0 bg-[url('/public/chess-pattern.svg')] opacity-5"></div>
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-20">
          <div className="text-center">
            <div className="flex justify-center items-center mb-8 animate-bounce-slow">
              <Crown className={`h-20 w-20 ${
                isDarkMode ? 'text-indigo-400' : 'text-indigo-600'
              }`} />
            </div>
            <h1 className={`text-5xl sm:text-6xl font-extrabold mb-6 animate-fade-in ${
              isDarkMode ? 'text-white' : 'text-gray-900'
            }`}>
              Elevate Your Chess Game
            </h1>
            <p className={`text-xl sm:text-2xl mb-12 max-w-3xl mx-auto animate-fade-in ${
              isDarkMode ? 'text-gray-300' : 'text-gray-600'
            }`}>
              Advanced AI analysis, performance tracking, and personalized insights to help you master the game of chess.
            </p>
            {!user && (
              <div className="flex flex-col sm:flex-row justify-center gap-4 animate-fade-in">
                <Link
                  to="/register"
                  className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-xl shadow-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors duration-200 transform hover:scale-105"
                >
                  Start Analyzing Free
                </Link>
                <Link
                  to="/login"
                  className={`inline-flex items-center px-8 py-4 border text-lg font-medium rounded-xl shadow-lg transition-all duration-200 transform hover:scale-105 ${
                    isDarkMode
                      ? 'border-gray-700 text-white hover:bg-gray-800'
                      : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  Sign In
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className={`py-24 ${
        isDarkMode ? 'bg-gray-800/50' : 'bg-white'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className={`text-4xl font-bold mb-4 ${
              isDarkMode ? 'text-white' : 'text-gray-900'
            }`}>
              Powerful Features
            </h2>
            <p className={`text-xl max-w-3xl mx-auto ${
              isDarkMode ? 'text-gray-300' : 'text-gray-600'
            }`}>
              Everything you need to analyze, understand, and improve your chess game
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <Feature key={index} {...feature} delay={index * 100} />
            ))}
          </div>
        </div>
      </div>

      {/* Testimonials Section */}
      {!user && (
        <div className="py-24">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className={`text-4xl font-bold mb-4 ${
                isDarkMode ? 'text-white' : 'text-gray-900'
              }`}>
                What Players Say
              </h2>
              <p className={`text-xl max-w-3xl mx-auto ${
                isDarkMode ? 'text-gray-300' : 'text-gray-600'
              }`}>
                Join thousands of chess players who have improved their game with ChessMate
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {testimonials.map((testimonial, index) => (
                <Testimonial key={index} {...testimonial} delay={index * 100} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* CTA Section */}
      {!user && (
        <div className="py-24">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className={`rounded-2xl shadow-2xl overflow-hidden transform hover:scale-[1.02] transition-transform duration-300 ${
              isDarkMode ? 'bg-gradient-to-br from-indigo-900 to-gray-900' : 'bg-gradient-to-br from-indigo-50 to-white'
            }`}>
              <div className="px-8 py-16 text-center relative">
                <div className="absolute inset-0 opacity-10 bg-[url('/chess-pattern.svg')]"></div>
                <div className="relative z-10">
                  <h2 className={`text-4xl font-bold mb-6 ${
                    isDarkMode ? 'text-white' : 'text-gray-900'
                  }`}>
                    Ready to Master Chess?
                  </h2>
                  <p className={`text-xl mb-10 max-w-2xl mx-auto ${
                    isDarkMode ? 'text-gray-300' : 'text-gray-600'
                  }`}>
                    Join ChessMate today and get access to powerful analysis tools, personalized insights, and a supportive community.
                  </p>
                  <Link
                    to="/register"
                    className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-xl shadow-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-all duration-200 transform hover:scale-105"
                  >
                    Start Your Journey
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;
