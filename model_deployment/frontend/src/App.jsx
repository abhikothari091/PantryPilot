import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './components/Toast';
import PageTransition from './components/PageTransition';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import RecipeGenerator from './pages/RecipeGenerator';
import Profile from './pages/Profile';
import History from './pages/History';

const PrivateRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-secondary-950">
        <div className="relative mb-6">
          <div className="w-16 h-16 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
        </div>
        <p className="text-slate-400 text-sm">Loading...</p>
      </div>
    );
  }

  return user ? children : <Navigate to="/login" />;
};

// Animated routes wrapper
const AnimatedRoutes = () => {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/login" element={
          <PageTransition>
            <Login />
          </PageTransition>
        } />
        <Route path="/signup" element={
          <PageTransition>
            <Signup />
          </PageTransition>
        } />

        <Route path="/dashboard" element={
          <PrivateRoute>
            <PageTransition>
              <Dashboard />
            </PageTransition>
          </PrivateRoute>
        } />

        <Route path="/recipes" element={
          <PrivateRoute>
            <PageTransition>
              <RecipeGenerator />
            </PageTransition>
          </PrivateRoute>
        } />

        <Route path="/profile" element={
          <PrivateRoute>
            <PageTransition>
              <Profile />
            </PageTransition>
          </PrivateRoute>
        } />

        <Route path="/history" element={
          <PrivateRoute>
            <PageTransition>
              <History />
            </PageTransition>
          </PrivateRoute>
        } />

        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </AnimatePresence>
  );
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <AnimatedRoutes />
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
