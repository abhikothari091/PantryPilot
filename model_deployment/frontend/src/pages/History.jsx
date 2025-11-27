import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, ThumbsUp, ThumbsDown, Minus, ChefHat, Calendar } from 'lucide-react';
import Layout from '../components/Layout';
import api from '../api/axios';

const History = () => {
    const [recipes, setRecipes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all'); // all, liked, disliked, neutral

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
        if (score === 2) return <ThumbsUp className="text-success-600" size={20} />;
        if (score === 1) return <ThumbsDown className="text-red-600" size={20} />;
        return <Minus className="text-slate-400" size={20} />;
    };

    const getFeedbackBadge = (score) => {
        if (score === 2) return 'badge-success';
        if (score === 1) return 'bg-red-100 text-red-700';
        return 'bg-slate-100 text-slate-600';
    };

    return (
        <Layout>
            <div className="mb-8">
                <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-600 via-accent-600 to-primary-600 bg-clip-text text-transparent">
                    Recipe History
                </h1>
                <p className="text-slate-500 mt-1">Your cooking journey</p>
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                {[
                    { key: 'all', label: 'All Recipes', count: recipes.length },
                    { key: 'liked', label: 'Liked', count: recipes.filter(r => r.feedback_score === 2).length },
                    { key: 'disliked', label: 'Disliked', count: recipes.filter(r => r.feedback_score === 1).length },
                    { key: 'neutral', label: 'No Feedback', count: recipes.filter(r => !r.feedback_score || r.feedback_score === 0).length }
                ].map(tab => (
                    <button
                        key={tab.key}
                        onClick={() => setFilter(tab.key)}
                        className={`px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${filter === tab.key
                                ? 'bg-gradient-to-r from-primary-600 to-accent-600 text-white shadow-lg'
                                : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
                            }`}
                    >
                        {tab.label} <span className="ml-1 opacity-75">({tab.count})</span>
                    </button>
                ))}
            </div>

            {/* Recipe Grid */}
            {loading ? (
                <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-500 border-t-transparent"></div>
                </div>
            ) : filteredRecipes.length === 0 ? (
                <div className="text-center py-12">
                    <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                        <ChefHat size={48} className="text-slate-400" />
                    </div>
                    <h3 className="text-xl font-semibold text-slate-900 mb-2">No recipes yet</h3>
                    <p className="text-slate-500">Start generating recipes to see them here!</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <AnimatePresence>
                        {filteredRecipes.map((recipe, index) => (
                            <motion.div
                                key={recipe.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ delay: index * 0.05 }}
                                className="card-premium p-6 cursor-pointer hover:scale-[1.02] transition-transform duration-200"
                            >
                                {/* Header */}
                                <div className="flex items-start justify-between mb-4">
                                    <h3 className="text-lg font-bold text-slate-900 line-clamp-2 flex-1">
                                        {getRecipeTitle(recipe)}
                                    </h3>
                                    <div className="ml-2">
                                        {getFeedbackIcon(recipe.feedback_score)}
                                    </div>
                                </div>

                                {/* Query */}
                                {recipe.user_query && (
                                    <p className="text-sm text-slate-600 mb-4 line-clamp-2 italic">
                                        "{recipe.user_query}"
                                    </p>
                                )}

                                {/* Metadata */}
                                <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                                    <div className="flex items-center gap-1">
                                        <Calendar size={14} />
                                        {formatDate(recipe.created_at)}
                                    </div>
                                </div>

                                {/* Badges */}
                                <div className="flex gap-2 flex-wrap">
                                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getFeedbackBadge(recipe.feedback_score)}`}>
                                        {recipe.feedback_score === 2 ? 'Liked' : recipe.feedback_score === 1 ? 'Disliked' : 'No Feedback'}
                                    </span>
                                    {recipe.is_cooked && (
                                        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-700 flex items-center gap-1">
                                            <ChefHat size={12} />
                                            Cooked
                                        </span>
                                    )}
                                </div>

                                {/* Cuisine if available */}
                                {recipe.recipe_json?.cuisine && (
                                    <div className="mt-3 pt-3 border-t border-slate-100">
                                        <span className="text-xs text-slate-500">
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
