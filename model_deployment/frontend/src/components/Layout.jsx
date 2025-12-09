import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LayoutDashboard, ChefHat, User, LogOut, ShoppingBasket, Clock, Sparkles, HelpCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import Snowfall from './Snowfall';
import { useToast } from './Toast';
import AppTour from './AppTour';

const Layout = ({ children }) => {
    const toast = useToast();
    const { logout, user } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();
    const [tourEnabled, setTourEnabled] = useState(false);

    const handleLogout = () => {
        logout();
        toast.info('See you soon! 👋');
        navigate('/login');
    };

    const toggleTour = () => {
        setTourEnabled(true);
    };

    const handleTourExit = () => {
        setTourEnabled(false);
    };

    const navItems = [
        { path: '/dashboard', icon: LayoutDashboard, label: 'Inventory', emoji: '🎄', id: 'nav-dashboard' },
        { path: '/recipes', icon: ChefHat, label: 'Recipes', emoji: '👨‍🍳', id: 'nav-recipes' },
        { path: '/history', icon: Clock, label: 'History', emoji: '📜', id: 'nav-history' },
        { path: '/profile', icon: User, label: 'Profile', emoji: '⚙️', id: 'nav-profile' },
    ];

    if (user?.username === 'admin') {
        navItems.push({ path: '/admin', icon: Sparkles, label: 'Admin', emoji: '👑' });
    }

    return (
        <div className="min-h-screen bg-secondary-950 flex relative overflow-hidden">
            <AppTour enabled={tourEnabled} onExit={handleTourExit} />

            {/* Subtle Background Effects */}
            <div className="fixed inset-0 bg-aurora pointer-events-none" />
            <Snowfall enabled={true} density="light" />

            {/* Sidebar */}
            <aside className="w-72 fixed h-full z-20 hidden md:flex flex-col glass-panel-solid border-r border-white/5">
                {/* Logo Section */}
                <div className="p-6 border-b border-white/5">
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-primary-500/30">
                                <ShoppingBasket size={26} />
                            </div>
                            {/* Festive sparkle */}
                            <Sparkles
                                size={14}
                                className="absolute -top-1 -right-1 text-gold-400 animate-twinkle"
                            />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold font-display text-gradient">
                                PantryPilot
                            </h1>
                            <p className="text-xs text-slate-500">AI Kitchen Assistant</p>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-1.5">
                    {navItems.map((item, index) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <motion.div
                                key={item.path}
                                id={item.id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.05 }}
                            >
                                <Link
                                    to={item.path}
                                    className={`group flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ${isActive
                                        ? 'bg-primary-500/15 text-primary-400 border border-primary-500/20 shadow-sm shadow-primary-500/10'
                                        : 'text-slate-400 hover:bg-white/5 hover:text-white border border-transparent'
                                        }`}
                                >
                                    <div className={`p-2 rounded-lg transition-all duration-300 ${isActive
                                        ? 'bg-primary-500/20'
                                        : 'bg-secondary-800/50 group-hover:bg-secondary-700/50'
                                        }`}>
                                        <item.icon
                                            size={18}
                                            className={isActive ? 'text-primary-400' : 'text-slate-500 group-hover:text-slate-300'}
                                        />
                                    </div>
                                    <span className="font-medium">{item.label}</span>
                                    {isActive && (
                                        <motion.div
                                            layoutId="activeIndicator"
                                            className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-400"
                                        />
                                    )}
                                </Link>
                            </motion.div>
                        );
                    })}
                </nav>

                {/* Tour Button - Above user section */}
                <div className="mx-4 mb-2">
                    <button
                        onClick={toggleTour}
                        className="w-full flex items-center gap-3 px-4 py-2 text-sm text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded-xl transition-all duration-200 group border border-dashed border-cyan-500/30 hover:border-cyan-500/50"
                    >
                        <HelpCircle size={16} />
                        <span>Start Tour</span>
                    </button>
                </div>

                {/* User Section */}
                <div className="p-4 border-t border-white/5" id="user-section">
                    <div className="flex items-center gap-3 px-4 py-3 mb-2 rounded-xl bg-secondary-800/30">
                        <div className="relative">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gold-400 to-gold-600 flex items-center justify-center text-secondary-900 font-bold text-sm shadow-lg shadow-gold-500/20">
                                {user?.username?.[0]?.toUpperCase()}
                            </div>
                            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-evergreen-500 rounded-full border-2 border-secondary-900" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-white truncate">{user?.username}</p>
                            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 rounded-xl transition-all duration-200 group"
                    >
                        <LogOut size={18} className="group-hover:translate-x-0.5 transition-transform" />
                        <span>Sign Out</span>
                    </button>
                </div>

                {/* Footer decoration */}
                <div className="px-6 py-4 border-t border-white/5">
                    <p className="text-xs text-center text-slate-600">
                        ❄️ Happy Holidays ❄️
                    </p>
                </div>
            </aside>

            {/* Mobile Header */}
            <div className="md:hidden fixed top-0 left-0 right-0 z-30 glass-panel-solid border-b border-white/5 px-4 py-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center text-white">
                            <ShoppingBasket size={18} />
                        </div>
                        <span className="font-bold font-display text-gradient">PantryPilot</span>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="p-2 text-slate-400 hover:text-white transition-colors"
                    >
                        <LogOut size={20} />
                    </button>
                </div>
            </div>

            {/* Mobile Bottom Navigation */}
            <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 glass-panel-solid border-t border-white/5 px-2 py-2">
                <div className="flex justify-around">
                    {navItems.map((item) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all ${isActive
                                    ? 'text-primary-400'
                                    : 'text-slate-500'
                                    }`}
                            >
                                <item.icon size={20} />
                                <span className="text-xs font-medium">{item.label}</span>
                            </Link>
                        );
                    })}
                </div>
            </nav>

            {/* Main Content */}
            <main className="flex-1 md:ml-72 min-h-screen pt-16 md:pt-0 pb-20 md:pb-0">
                <div className="p-6 md:p-8 max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                    >
                        {children}
                    </motion.div>
                </div>
            </main>
        </div>
    );
};

export default Layout;
