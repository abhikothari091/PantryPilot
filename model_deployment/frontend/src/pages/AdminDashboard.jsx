import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    Users, ChefHat, Package, TrendingUp, ThumbsUp, ThumbsDown,
    Activity, BarChart3, PieChart, Clock, AlertTriangle, Crown,
    Utensils, Scale, Layers
} from 'lucide-react';
import api from '../api/axios';
import Layout from '../components/Layout';

export default function AdminDashboard() {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchMetrics();
    }, []);

    const fetchMetrics = async () => {
        try {
            const response = await api.get('/admin/metrics');
            setMetrics(response.data);
            setError(null);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load metrics');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-secondary-950">
                <div className="animate-spin rounded-full h-16 w-16 border-4 border-primary-500 border-t-transparent"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-secondary-950">
                <div className="glass-panel p-8 text-center max-w-md">
                    <AlertTriangle className="w-16 h-16 text-red-400 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
                    <p className="text-white/60 mb-6">{error}</p>
                    <a href="/dashboard" className="btn-primary block w-full">Return to Dashboard</a>
                </div>
            </div>
        );
    }

    const { users, recipes, inventory, dpo, top_users } = metrics;

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between"
                >
                    <div>
                        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                            <Crown className="w-8 h-8 text-yellow-400" />
                            Admin Dashboard
                        </h1>
                        <p className="text-white/60 mt-1">Real-time analytics and insights</p>
                    </div>
                    <button
                        onClick={fetchMetrics}
                        className="btn-primary flex items-center gap-2"
                    >
                        <Activity className="w-4 h-4" />
                        Refresh
                    </button>
                </motion.div>

                {/* Key Metrics Row */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
                >
                    <MetricCard
                        icon={Users}
                        label="Total Users"
                        value={users.total}
                        subValue={`+${users.new_7d} this week`}
                        color="blue"
                    />
                    <MetricCard
                        icon={ChefHat}
                        label="Recipes Generated"
                        value={recipes.total}
                        subValue={`${recipes.last_7d} this week`}
                        color="emerald"
                    />
                    <MetricCard
                        icon={Package}
                        label="Inventory Items"
                        value={inventory.total_items}
                        subValue={`${inventory.low_stock} low stock`}
                        color="purple"
                        alert={inventory.low_stock > 0}
                    />
                    <MetricCard
                        icon={Scale}
                        label="DPO Comparisons"
                        value={dpo.total_comparisons}
                        subValue={`${dpo.completion_rate}% completed`}
                        color="orange"
                    />
                </motion.div>

                {/* Charts Row */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Recipe Generation Chart */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                        className="glass-panel p-6"
                    >
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-emerald-400" />
                            Recipe Generation (Last 7 Days)
                        </h3>
                        <div className="h-48 flex items-end gap-2">
                            {recipes.by_day.map((day, i) => {
                                const maxCount = Math.max(...recipes.by_day.map(d => d.count), 1);
                                const height = (day.count / maxCount) * 100;
                                return (
                                    <div key={i} className="flex-1 h-full flex flex-col justify-end items-center gap-1 group">
                                        <span className="text-sm font-bold text-white mb-1 opacity-60 group-hover:opacity-100 transition-opacity">
                                            {day.count}
                                        </span>
                                        <motion.div
                                            initial={{ height: 0 }}
                                            animate={{ height: `${Math.max(height, 5)}%` }}
                                            transition={{ delay: 0.3 + i * 0.05 }}
                                            className="w-full bg-gradient-to-t from-emerald-500 to-emerald-400 rounded-t-lg relative group-hover:from-emerald-400 group-hover:to-emerald-300 transition-colors shadow-[0_0_10px_rgba(16,185,129,0.3)]"
                                        />
                                        <span className="text-xs text-white/50 font-medium">{day.date.split(' ')[1]}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </motion.div>

                    {/* Feedback Distribution */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                        className="glass-panel p-6"
                    >
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <PieChart className="w-5 h-5 text-blue-400" />
                            User Engagement Rates
                        </h3>
                        <div className="grid grid-cols-3 gap-4">
                            <EngagementRing
                                value={recipes.feedback_rate}
                                label="Feedback Rate"
                                color="blue"
                            />
                            <EngagementRing
                                value={recipes.cook_rate}
                                label="Cook Rate"
                                color="emerald"
                            />
                            <EngagementRing
                                value={recipes.like_rate}
                                label="Like Rate"
                                color="purple"
                            />
                        </div>
                        <div className="mt-4 flex justify-center gap-6 text-sm">
                            <div className="flex items-center gap-2">
                                <ThumbsUp className="w-4 h-4 text-emerald-400" />
                                <span className="text-white/80">{recipes.liked} likes</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <ThumbsDown className="w-4 h-4 text-red-400" />
                                <span className="text-white/80">{recipes.disliked} dislikes</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Utensils className="w-4 h-4 text-yellow-400" />
                                <span className="text-white/80">{recipes.cooked} cooked</span>
                            </div>
                        </div>
                    </motion.div>
                </div>

                {/* Bottom Row */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Top Users */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="glass-panel p-6"
                    >
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-yellow-400" />
                            Top Users
                        </h3>
                        <div className="space-y-3">
                            {top_users.length === 0 ? (
                                <p className="text-white/50 text-center py-4">No user activity yet</p>
                            ) : (
                                top_users.map((user, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                                        <div className="flex items-center gap-3">
                                            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-yellow-500 text-black' :
                                                i === 1 ? 'bg-gray-400 text-black' :
                                                    i === 2 ? 'bg-amber-600 text-white' :
                                                        'bg-white/10 text-white'
                                                }`}>
                                                {i + 1}
                                            </span>
                                            <span className="text-white">{user.username}</span>
                                        </div>
                                        <span className="text-white/60">{user.recipes} recipes</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </motion.div>

                    {/* Inventory Categories */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="glass-panel p-6"
                    >
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Layers className="w-5 h-5 text-purple-400" />
                            Inventory Categories
                        </h3>
                        <div className="space-y-3">
                            {inventory.categories.length === 0 ? (
                                <p className="text-white/50 text-center py-4">No inventory data yet</p>
                            ) : (
                                inventory.categories.map((cat, i) => {
                                    const maxCount = Math.max(...inventory.categories.map(c => c.count), 1);
                                    const width = (cat.count / maxCount) * 100;
                                    return (
                                        <div key={i} className="space-y-1">
                                            <div className="flex justify-between text-sm">
                                                <span className="text-white capitalize">{cat.category}</span>
                                                <span className="text-white/60">{cat.count}</span>
                                            </div>
                                            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${width}%` }}
                                                    transition={{ delay: 0.5 + i * 0.1 }}
                                                    className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full"
                                                />
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </motion.div>

                    {/* DPO Stats */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        className="glass-panel p-6"
                    >
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Scale className="w-5 h-5 text-orange-400" />
                            DPO Training Data
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="text-center p-4 bg-white/5 rounded-xl">
                                <div className="text-3xl font-bold text-emerald-400">{dpo.completed}</div>
                                <div className="text-sm text-white/60 mt-1">Completed</div>
                            </div>
                            <div className="text-center p-4 bg-white/5 rounded-xl">
                                <div className="text-3xl font-bold text-orange-400">{dpo.skipped}</div>
                                <div className="text-sm text-white/60 mt-1">Skipped</div>
                            </div>
                        </div>
                        <div className="mt-4 p-4 bg-white/5 rounded-xl">
                            <div className="flex justify-between items-center">
                                <span className="text-white/60">Completion Rate</span>
                                <span className="text-xl font-bold text-white">{dpo.completion_rate}%</span>
                            </div>
                            <div className="mt-2 h-3 bg-white/10 rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${dpo.completion_rate}%` }}
                                    transition={{ delay: 0.7 }}
                                    className="h-full bg-gradient-to-r from-orange-600 to-orange-400 rounded-full"
                                />
                            </div>
                        </div>
                    </motion.div>
                </div>

                {/* Active Users Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7 }}
                    className="glass-panel p-6"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                                <Clock className="w-5 h-5 text-cyan-400" />
                                User Activity (Last 7 Days)
                            </h3>
                            <p className="text-white/60 text-sm mt-1">
                                {users.active_7d} active users out of {users.total} total
                            </p>
                        </div>
                        <div className="text-right">
                            <div className="text-4xl font-bold text-cyan-400">
                                {users.total > 0 ? Math.round((users.active_7d / users.total) * 100) : 0}%
                            </div>
                            <div className="text-sm text-white/60">Activity Rate</div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </Layout>
    );
}

// Metric Card Component
function MetricCard({ icon: Icon, label, value, subValue, color, alert }) {
    const colorClasses = {
        blue: 'from-blue-600 to-blue-400',
        emerald: 'from-emerald-600 to-emerald-400',
        purple: 'from-purple-600 to-purple-400',
        orange: 'from-orange-600 to-orange-400',
    };

    return (
        <div className="glass-panel p-5 relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${colorClasses[color]} opacity-10 rounded-full translate-x-8 -translate-y-8`} />
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-white/60 text-sm">{label}</p>
                    <p className="text-3xl font-bold text-white mt-1">{value.toLocaleString()}</p>
                    <p className={`text-sm mt-1 ${alert ? 'text-orange-400' : 'text-white/50'}`}>
                        {subValue}
                    </p>
                </div>
                <div className={`p-3 rounded-xl bg-gradient-to-br ${colorClasses[color]}`}>
                    <Icon className="w-6 h-6 text-white" />
                </div>
            </div>
        </div>
    );
}

// Engagement Ring Component
function EngagementRing({ value, label, color }) {
    const colorClasses = {
        blue: 'text-blue-400',
        emerald: 'text-emerald-400',
        purple: 'text-purple-400',
    };

    const strokeColor = {
        blue: '#3b82f6',
        emerald: '#10b981',
        purple: '#a855f7',
    };

    const circumference = 2 * Math.PI * 40;
    const strokeDashoffset = circumference - (value / 100) * circumference;

    return (
        <div className="flex flex-col items-center">
            <div className="relative w-24 h-24">
                <svg className="w-24 h-24 transform -rotate-90">
                    <circle
                        cx="48"
                        cy="48"
                        r="40"
                        stroke="rgba(255,255,255,0.1)"
                        strokeWidth="8"
                        fill="none"
                    />
                    <motion.circle
                        cx="48"
                        cy="48"
                        r="40"
                        stroke={strokeColor[color]}
                        strokeWidth="8"
                        fill="none"
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        initial={{ strokeDashoffset: circumference }}
                        animate={{ strokeDashoffset }}
                        transition={{ duration: 1, delay: 0.5 }}
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-xl font-bold ${colorClasses[color]}`}>{value}%</span>
                </div>
            </div>
            <span className="text-xs text-white/60 mt-2 text-center">{label}</span>
        </div>
    );
}
