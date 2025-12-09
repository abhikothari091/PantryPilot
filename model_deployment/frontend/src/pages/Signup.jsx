import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Sparkles, UserPlus, Mail, User, Lock } from 'lucide-react';
import Snowfall from '../components/Snowfall';
import { useToast } from '../components/Toast';

const Signup = () => {
    const toast = useToast();
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await register(username, email, password);
            toast.success(`Welcome to PantryPilot, ${username}! 🎉`);
            navigate('/dashboard');
        } catch (err) {
            // Show actual error from backend for debugging
            const detail = err.response?.data?.detail || err.message || 'Registration failed';
            setError(detail);
            console.error('Registration error:', err.response?.data || err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-secondary-950">
            {/* Animated Background */}
            <div className="absolute inset-0">
                {/* Aurora gradient effects */}
                <div className="absolute top-0 left-0 w-full h-full">
                    <motion.div
                        animate={{
                            scale: [1.2, 1, 1.2],
                            opacity: [0.2, 0.4, 0.2],
                        }}
                        transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
                        className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-evergreen-500/15 rounded-full blur-[120px]"
                    />
                    <motion.div
                        animate={{
                            scale: [1, 1.2, 1],
                            opacity: [0.3, 0.5, 0.3],
                        }}
                        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
                        className="absolute bottom-[-20%] left-[-10%] w-[600px] h-[600px] bg-primary-500/20 rounded-full blur-[120px]"
                    />
                    <motion.div
                        animate={{
                            scale: [1.1, 1, 1.1],
                            opacity: [0.15, 0.3, 0.15],
                        }}
                        transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
                        className="absolute top-[40%] left-[30%] w-[400px] h-[400px] bg-gold-500/10 rounded-full blur-[100px]"
                    />
                </div>

                {/* Subtle pattern overlay */}
                <div className="absolute inset-0 bg-pattern-dots opacity-30" />
            </div>

            {/* Snowfall */}
            <Snowfall enabled={true} density="normal" />

            {/* Signup Card */}
            <motion.div
                initial={{ opacity: 0, y: 30, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
                className="relative z-10 w-full max-w-md mx-4"
            >
                <div className="glass-panel-solid rounded-3xl p-8 shadow-2xl border border-white/10">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-evergreen-500 to-evergreen-600 shadow-lg shadow-evergreen-500/30 mb-4"
                        >
                            <UserPlus size={32} className="text-white" />
                        </motion.div>
                        <h2 className="text-3xl font-bold font-display text-gradient mb-2">
                            Join the Feast
                        </h2>
                        <p className="text-slate-400 flex items-center justify-center gap-2">
                            <Sparkles size={14} className="text-gold-400" />
                            Create your account
                            <Sparkles size={14} className="text-gold-400" />
                        </p>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl mb-6 text-center text-sm"
                        >
                            {error}
                        </motion.div>
                    )}

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Username
                            </label>
                            <div className="relative">
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="input-field-dark pl-11"
                                    placeholder="Choose a username"
                                    required
                                    autoComplete="username"
                                />
                                <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Email
                            </label>
                            <div className="relative">
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="input-field-dark pl-11"
                                    placeholder="Enter your email"
                                    required
                                    autoComplete="email"
                                />
                                <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Password
                            </label>
                            <div className="relative">
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="input-field-dark pl-11 pr-12"
                                    placeholder="Create a password"
                                    required
                                    autoComplete="new-password"
                                />
                                <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors p-1"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <motion.button
                            type="submit"
                            disabled={loading}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="w-full bg-gradient-to-r from-evergreen-600 to-evergreen-500 hover:from-evergreen-500 hover:to-evergreen-400 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-evergreen-500/25 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-6"
                        >
                            {loading ? (
                                <>
                                    <motion.div
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                        className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                                    />
                                    Creating account...
                                </>
                            ) : (
                                <>
                                    <Sparkles size={18} />
                                    Create Account
                                </>
                            )}
                        </motion.button>
                    </form>

                    {/* Footer */}
                    <div className="mt-8 pt-6 border-t border-white/5">
                        <p className="text-center text-slate-400">
                            Already have an account?{' '}
                            <Link
                                to="/login"
                                className="text-primary-400 hover:text-primary-300 font-medium transition-colors"
                            >
                                Sign in
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Decorative footer text */}
                <p className="text-center text-slate-600 text-sm mt-6">
                    🎄 Start your culinary journey today 🎄
                </p>
            </motion.div>
        </div>
    );
};

export default Signup;
