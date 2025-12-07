import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, ThumbsUp, ThumbsDown, Minus, ChefHat, Calendar, Sparkles, BookOpen } from 'lucide-react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { SkeletonHistoryGrid } from '../components/Skeleton';

const History = () => {
    const [recipes, setRecipes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        try {
            const res = await api.get('/recipes/history');
            setRecipes(res.data);
        } catch (err) {
            console.error('Failed to fetch history', err);
        } finally {
            setLoading(false);
        }
    };

    const filteredRecipes = recipes.filter(recipe => {
        if (filter === 'all') return true;
        if (filter === 'liked') return recipe.feedback_score === 2;
        if (filter === 'disliked') return recipe.feedback_score === 1;
        if (filter === 'neutral') return !recipe.feedback_score || recipe.feedback_score === 0;
        return true;
    });

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getRecipeTitle = (recipe) => {
        return recipe.recipe_json?.name ||
            recipe.recipe_json?.recipe?.name ||
            recipe.user_query ||
            'Untitled Recipe';
    };

    const getFeedbackIcon = (score) => {
        if (score === 2) return <ThumbsUp className="text-evergreen-400" size={18} />;
        if (score === 1) return <ThumbsDown className="text-red-400" size={18} />;
        return <Minus className="text-slate-500" size={18} />;
    };

    const getFeedbackBadge = (score) => {
        if (score === 2) return 'bg-evergreen-500/20 text-evergreen-400 border-evergreen-500/30';
        if (score === 1) return 'bg-red-500/20 text-red-400 border-red-500/30';
        return 'bg-secondary-700/50 text-slate-400 border-white/10';
    };

    const filterTabs = [
        { key: 'all', label: 'All Recipes', count: recipes.length, icon: BookOpen },
        { key: 'liked', label: 'Liked', count: recipes.filter(r => r.feedback_score === 2).length, icon: ThumbsUp },
        { key: 'disliked', label: 'Disliked', count: recipes.filter(r => r.feedback_score === 1).length, icon: ThumbsDown },
        { key: 'neutral', label: 'No Feedback', count: recipes.filter(r => !r.feedback_score || r.feedback_score === 0).length, icon: Minus }
    ];

    return (
        <Layout>
            {/* Header */}
            <div className="mb-8">
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <h1 className="text-3xl md:text-4xl font-bold font-display text-gradient mb-2">
                        Recipe History
                    </h1>
                    <p className="text-slate-400 flex items-center gap-2">
                        <Sparkles size={16} className="text-gold-400" />
                        Your culinary journey
                    </p>
                </motion.div>
            </div>

            {/* Filter Tabs */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="flex gap-2 mb-8 overflow-x-auto pb-2 scrollbar-hide"
            >
                {filterTabs.map((tab, index) => {
                    const Icon = tab.icon;
                    return (
                        <motion.button
                            key={tab.key}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            onClick={() => setFilter(tab.key)}
                            className={`px-4 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap flex items-center gap-2 ${filter === tab.key
                                ? 'bg-gradient-to-r from-primary-600 to-gold-500 text-white shadow-lg shadow-primary-500/20'
                                : 'glass-frost text-slate-400 hover:text-white hover:bg-white/10 border border-white/5'
                                }`}
                        >
                            <Icon size={16} />
                            {tab.label}
                            <span className={`text-xs px-1.5 py-0.5 rounded-md ${filter === tab.key ? 'bg-white/20' : 'bg-secondary-700'
                                }`}>
                                {tab.count}
                            </span>
                        </motion.button>
                    );
                })}
            </motion.div>

            {/* Recipe Grid */}
            {loading ? (
                <SkeletonHistoryGrid count={6} />
            ) : filteredRecipes.length === 0 ? (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center py-20"
                >
                    <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-secondary-800/50 flex items-center justify-center">
                        <ChefHat size={48} className="text-slate-600" />
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">
                        {filter === 'all' ? 'No recipes yet' : `No ${filter} recipes`}
                    </h3>
                    <p className="text-slate-400">
                        {filter === 'all'
                            ? 'Start generating recipes to see them here!'
                            : 'Try a different filter to see more recipes.'}
                    </p>
                </motion.div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <AnimatePresence>
                        {filteredRecipes.map((recipe, index) => (
                            <motion.div
                                key={recipe.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ delay: index * 0.03 }}
                                className="card-premium p-5 cursor-pointer group"
                            >
                                {/* Header */}
                                <div className="flex items-start justify-between mb-3">
                                    <h3 className="text-lg font-bold text-white line-clamp-2 flex-1 group-hover:text-primary-400 transition-colors">
                                        {getRecipeTitle(recipe)}
                                    </h3>
                                    <div className="ml-3 p-2 rounded-lg bg-secondary-800/50">
                                        {getFeedbackIcon(recipe.feedback_score)}
                                    </div>
                                </div>

                                {/* Query */}
                                {recipe.user_query && (
                                    <p className="text-sm text-slate-500 mb-4 line-clamp-2 italic">
                                        "{recipe.user_query}"
                                    </p>
                                )}

                                {/* Metadata */}
                                <div className="flex items-center gap-3 text-xs text-slate-500 mb-4">
                                    <div className="flex items-center gap-1.5">
                                        <Calendar size={14} />
                                        {formatDate(recipe.created_at)}
                                    </div>
                                </div>

                                {/* Badges */}
                                <div className="flex gap-2 flex-wrap">
                                    <span className={`badge border ${getFeedbackBadge(recipe.feedback_score)}`}>
                                        {recipe.feedback_score === 2 ? 'Liked' : recipe.feedback_score === 1 ? 'Disliked' : 'No Feedback'}
                                    </span>
                                    {recipe.is_cooked && (
                                        <span className="badge bg-primary-500/20 text-primary-400 border border-primary-500/30 flex items-center gap-1">
                                            <ChefHat size={12} />
                                            Cooked
                                        </span>
                                    )}
                                </div>

                                {/* Cuisine */}
                                {recipe.recipe_json?.cuisine && (
                                    <div className="mt-4 pt-3 border-t border-white/5">
                                        <span className="text-xs text-slate-500 flex items-center gap-1.5">
                                            🍽️ {recipe.recipe_json.cuisine}
                                        </span>
                                    </div>
                                )}
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </Layout>
    );
};

export default History;
