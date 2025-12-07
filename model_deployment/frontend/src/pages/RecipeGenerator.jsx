import React, { useRef, useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Send, ThumbsUp, ThumbsDown, CheckCircle, Loader2, Sparkles, ChefHat, AlertCircle, Clock, Utensils, Play } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '../components/Toast';

const RecipeGenerator = () => {
    const toast = useToast();
    const [query, setQuery] = useState('');
    const [servings, setServings] = useState(2);
    const [loading, setLoading] = useState(false);
    const [recipe, setRecipe] = useState(null);
    const [historyId, setHistoryId] = useState(null);
    const [feedback, setFeedback] = useState(null);
    const [cooked, setCooked] = useState(false);
    const [error, setError] = useState('');
    const [comparisonMode, setComparisonMode] = useState(false);
    const [comparisonData, setComparisonData] = useState({ variantA: null, variantB: null });
    const [preferenceId, setPreferenceId] = useState(null);
    const [selectedVariant, setSelectedVariant] = useState(null);
    const [choiceSubmitting, setChoiceSubmitting] = useState(false);
    const [skipSubmitting, setSkipSubmitting] = useState(false);
    const [comparisonError, setComparisonError] = useState('');
    const [inventory, setInventory] = useState([]);
    const [warning, setWarning] = useState('');
    const LOW_STOCK_THRESHOLD = 0.1;

    const [showVideoModal, setShowVideoModal] = useState(false);
    const [videoGenerating, setVideoGenerating] = useState(false);
    const [videoProgress, setVideoProgress] = useState(0);
    const [videoUrl, setVideoUrl] = useState('');
    const [videoError, setVideoError] = useState('');
    const progressTimerRef = useRef(null);
    const VIDEO_MOCK_URL = 'https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4';

    React.useEffect(() => () => cleanupProgressTimer(), []);

    const parseSteps = (steps) => {
        if (Array.isArray(steps)) {
            return steps.map((s) => (typeof s === 'string' ? s.trim() : '')).filter(Boolean);
        }
        if (typeof steps !== 'string') return [];

        const cleaned = steps.replace(/\r/g, '').trim();
        if (!cleaned) return [];

        const splitByMarkers = (text) => {
            const markers = [...text.matchAll(/step\s*\d+[.:-]?\s*/gi)];
            if (markers.length === 0) return [];
            const parts = [];
            markers.forEach((m, idx) => {
                const start = m.index + m[0].length;
                const end = idx + 1 < markers.length ? markers[idx + 1].index : text.length;
                const chunk = text.slice(start, end).trim();
                if (chunk) parts.push(chunk);
            });
            return parts;
        };

        const stepParts = splitByMarkers(cleaned);
        if (stepParts.length) return stepParts;

        const bulletMatches = cleaned.match(/^\s*[-*]\s+/m);
        if (bulletMatches) {
            return cleaned
                .split(/\n+/)
                .map((line) => line.replace(/^\s*[-*]\s+/, '').trim())
                .filter(Boolean);
        }

        const stepRegex = /(?:^|\n)\s*Step\s*\d+[.:\-\s]*/gi;
        if (cleaned.match(stepRegex)) {
            return cleaned.split(stepRegex).map((s) => s.trim()).filter(Boolean);
        }

        return cleaned
            .split(/\n+/)
            .flatMap((chunk) => chunk.split(/(?<=[.!?])\s+/))
            .map((s) => s.trim())
            .filter(Boolean);
    };

    const parseRecipeResponse = (content) => {
        let parsed = { raw_text: 'Unable to parse recipe' };

        if (typeof content === 'object' && content !== null) {
            parsed = content;
        } else if (typeof content === 'string') {
            try {
                const codeBlockMatch = content.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
                if (codeBlockMatch) {
                    parsed = JSON.parse(codeBlockMatch[1]);
                } else {
                    const firstOpen = content.indexOf('{');
                    if (firstOpen !== -1) {
                        let balance = 0;
                        let lastClose = -1;
                        let inString = false;
                        let escape = false;

                        for (let i = firstOpen; i < content.length; i++) {
                            const char = content[i];
                            if (escape) { escape = false; continue; }
                            if (char === '\\') { escape = true; continue; }
                            if (char === '"') { inString = !inString; continue; }
                            if (!inString) {
                                if (char === '{') balance++;
                                else if (char === '}') {
                                    balance--;
                                    if (balance === 0) { lastClose = i; break; }
                                }
                            }
                        }

                        if (lastClose !== -1) {
                            try {
                                parsed = JSON.parse(content.substring(firstOpen, lastClose + 1));
                            } catch {
                                const jsonMatch = content.match(/\{[\s\S]*\}/);
                                if (jsonMatch) {
                                    try { parsed = JSON.parse(jsonMatch[0]); } catch { parsed = { raw_text: content }; }
                                } else { parsed = { raw_text: content }; }
                            }
                        } else {
                            const jsonMatch = content.match(/\{[\s\S]*\}/);
                            if (jsonMatch) {
                                try { parsed = JSON.parse(jsonMatch[0]); } catch { parsed = { raw_text: content }; }
                            } else { parsed = { raw_text: content }; }
                        }
                    } else { parsed = { raw_text: content }; }
                }
            } catch { parsed = { raw_text: content }; }
        }

        const recipeNode = parsed.recipe || parsed;
        const stepsFromRecipe = parseSteps(recipeNode.steps);
        const stepsFromRaw = stepsFromRecipe.length ? stepsFromRecipe : parseSteps(parsed.raw_text || '');

        return {
            ...parsed,
            parsedSteps: stepsFromRecipe.length ? stepsFromRecipe : stepsFromRaw,
        };
    };

    // Detect if the LLM response indicates it couldn't generate a valid recipe
    const isRecipeError = (recipe) => {
        if (!recipe) return true;

        const rawText = (recipe.raw_text || '').toLowerCase();
        const name = (recipe.recipe?.name || recipe.name || '').toLowerCase();
        const steps = recipe.parsedSteps || [];

        // Check for error indicators in the response
        const errorPhrases = [
            'no suitable recipe',
            'cannot be made',
            'no recipe found',
            'failed to parse',
            'unable to',
            'not possible',
            'cannot generate',
            'no sweet dessert',
            'no dessert can be made',
            'ingredients provided'
        ];

        const hasErrorPhrase = errorPhrases.some(phrase =>
            rawText.includes(phrase) || name.includes(phrase) ||
            steps.some(s => s.toLowerCase().includes(phrase))
        );

        // Check if name is generic error
        const isErrorName = name === 'error' || name === 'unknown' || name === '';

        // Check if steps look like error messages rather than cooking instructions
        const stepsLookLikeError = steps.length > 0 && steps.every(s =>
            s.toLowerCase().includes('error') ||
            s.toLowerCase().includes('failed') ||
            s.toLowerCase().includes('no suitable') ||
            s.toLowerCase().includes('raw output')
        );

        return hasErrorPhrase || isErrorName || stepsLookLikeError;
    };

    const renderVariantCard = (variant, label) => {
        if (!variant) return null;
        const title = variant.recipe?.name || variant.name || `Variant ${label}`;
        const cuisine = variant.recipe?.cuisine || variant.cuisine;
        const time = variant.recipe?.time || variant.time;
        const ingredients = variant.recipe?.main_ingredients || variant.main_ingredients || [];
        const steps = variant.parsedSteps || [];
        const isSelected = selectedVariant === label;

        return (
            <motion.button
                type="button"
                onClick={() => setSelectedVariant(label)}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className={`flex-1 text-left rounded-2xl p-6 transition-all duration-300 ${isSelected
                    ? 'bg-primary-500/10 border-2 border-primary-500/50 shadow-glow-primary'
                    : 'glass-panel-solid border border-white/10 hover:border-primary-500/30'
                    }`}
            >
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <span className={`px-3 py-1.5 rounded-lg text-sm font-bold ${isSelected
                            ? 'bg-primary-500 text-white'
                            : 'bg-secondary-700 text-slate-300'
                            }`}>
                            {label}
                        </span>
                        <h3 className="text-lg font-bold text-white">{title}</h3>
                    </div>
                    {isSelected && <CheckCircle className="text-primary-400" size={22} />}
                </div>
                <div className="flex gap-2 flex-wrap mb-4">
                    {cuisine && <span className="badge-gold">🍽️ {cuisine}</span>}
                    {time && <span className="badge-frost">⏱️ {time}</span>}
                </div>
                <div className="space-y-4">
                    <div>
                        <h4 className="font-semibold text-slate-300 mb-2 text-sm">Ingredients</h4>
                        <ul className="space-y-1 text-slate-400 text-sm max-h-24 overflow-y-auto scrollbar-hide">
                            {ingredients.slice(0, 5).map((ing, idx) => (
                                <li key={idx} className="flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary-500" />
                                    {typeof ing === 'string' ? ing : ing?.name || JSON.stringify(ing)}
                                </li>
                            ))}
                            {ingredients.length > 5 && (
                                <li className="text-slate-500">+{ingredients.length - 5} more</li>
                            )}
                        </ul>
                    </div>
                    <div>
                        <h4 className="font-semibold text-slate-300 mb-2 text-sm">Instructions</h4>
                        <ul className="space-y-1 text-slate-400 text-sm max-h-24 overflow-y-auto scrollbar-hide">
                            {steps.length ? steps.slice(0, 3).map((s, i) => (
                                <li key={i} className="line-clamp-1">• {s}</li>
                            )) : <li className="text-slate-500">Steps not provided</li>}
                            {steps.length > 3 && <li className="text-slate-500">+{steps.length - 3} more steps</li>}
                        </ul>
                    </div>
                </div>
            </motion.button>
        );
    };

    const normalizeName = (str = '') => str.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();

    const hasInventoryItem = (name) => {
        const normName = normalizeName(name);
        return inventory.some((item) => {
            const invNorm = normalizeName(item.item_name);
            return invNorm && normName && (invNorm.includes(normName) || normName.includes(invNorm));
        });
    };

    const fetchInventory = React.useCallback(async () => {
        try {
            const res = await api.get('/inventory/');
            setInventory(res.data || []);
        } catch (e) {
            console.error('Inventory fetch failed', e);
        }
    }, []);

    React.useEffect(() => {
        fetchInventory();
    }, [fetchInventory]);

    const handleGenerate = async () => {
        if (!query.trim()) return;

        setLoading(true);
        setError('');
        setRecipe(null);
        setComparisonMode(false);
        setComparisonData({ variantA: null, variantB: null });
        setPreferenceId(null);
        setSelectedVariant(null);
        setComparisonError('');
        setFeedback(null);
        setCooked(false);
        setWarning('');

        try {
            const res = await api.post('/recipes/generate', {
                user_request: `${query} (for ${servings} servings)`,
                servings: servings
            });
            if (res.data.status === 'success') {
                if (res.data.mode === 'comparison') {
                    const variantA = parseRecipeResponse(res.data.data.variant_a);
                    const variantB = parseRecipeResponse(res.data.data.variant_b);
                    setComparisonData({ variantA, variantB });
                    setPreferenceId(res.data.preference_id);
                    setComparisonMode(true);
                    setLoading(false);
                    return;
                }

                const recipeData = parseRecipeResponse(res.data.data.recipe);
                setRecipe(recipeData);
                setHistoryId(res.data.history_id);
                fetchInventory();

                const maybeProtein = query.toLowerCase();
                const lacksChicken = maybeProtein.includes('chicken') && !hasInventoryItem('chicken');
                const lacksMain = (recipeData.recipe?.main_ingredients || []).some(
                    (ing) => !hasInventoryItem(ing)
                );
                if (lacksChicken || lacksMain) {
                    setWarning('Your inventory may be missing some ingredients; please verify before cooking.');
                }
            } else {
                setError('Failed to generate recipe. Please try again.');
            }
        } catch (err) {
            console.error('Recipe generation error:', err);
            setError('An error occurred. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleConfirmChoice = async () => {
        if (!preferenceId || !selectedVariant) return;
        setChoiceSubmitting(true);
        setComparisonError('');
        try {
            const res = await api.post(`/recipes/preference/${preferenceId}/choose`, {
                chosen_variant: selectedVariant,
                servings
            });
            const chosenData = selectedVariant === 'A' ? comparisonData.variantA : comparisonData.variantB;
            setRecipe(chosenData);
            setHistoryId(res.data.history_id);
            setComparisonMode(false);
            setSelectedVariant(null);
            fetchInventory();
        } catch (err) {
            console.error('Choice failed', err);
            setComparisonError('Failed to save your choice. Please try again.');
        } finally {
            setChoiceSubmitting(false);
        }
    };

    const handleSkipComparison = async () => {
        if (!preferenceId) return;
        setSkipSubmitting(true);
        setComparisonError('');
        try {
            await api.post(`/recipes/preference/${preferenceId}/skip`, { reason: 'user_skip' });
            setComparisonMode(false);
            setSelectedVariant(null);
            setPreferenceId(null);
            await handleGenerate();
        } catch (err) {
            console.error('Skip failed', err);
            setComparisonError('Failed to skip. Please try again.');
        } finally {
            setSkipSubmitting(false);
        }
    };

    const handleFeedback = async (score) => {
        if (!historyId) return;
        try {
            await api.post(`/recipes/${historyId}/feedback`, { score });
            setFeedback(score);
            toast.success(score === 2 ? 'Glad you liked it! 👍' : 'Thanks for feedback!');
        } catch (err) {
            console.error(err);
            toast.error('Failed to save feedback');
        }
    };

    const handleCooked = async () => {
        if (!historyId) return;
        try {
            await api.post(`/recipes/${historyId}/cooked`);
            setCooked(true);
            await fetchInventory();
            toast.success('Marked as cooked! Inventory updated 🍳');
        } catch (err) {
            console.error(err);
            toast.error('Failed to mark as cooked');
        }
    };

    const cleanupProgressTimer = () => {
        if (progressTimerRef.current) {
            clearInterval(progressTimerRef.current);
            progressTimerRef.current = null;
        }
    };

    const handleVideoConfirm = async () => {
        setShowVideoModal(false);
        setVideoError('');
        setVideoUrl('');
        setVideoGenerating(true);
        setVideoProgress(0);

        try {
            const prompt = recipe?.recipe?.name || recipe?.name || (query ? `Cooking video for: ${query}` : 'Cooking video');
            cleanupProgressTimer();
            setVideoProgress(12);
            progressTimerRef.current = setInterval(() => {
                setVideoProgress((p) => Math.min(90, p + 6 + Math.random() * 4));
            }, 320);

            const res = await api.post('/recipes/video', { prompt });
            const url = res?.data?.video_url || VIDEO_MOCK_URL;
            setVideoUrl(url);
            setVideoProgress(100);
        } catch (err) {
            console.error('Video generation failed', err);
            setVideoError('Video generation failed. Please try again.');
        } finally {
            cleanupProgressTimer();
            setVideoGenerating(false);
        }
    };

    const videoStatusLabel = () => {
        if (videoGenerating) return 'Generating video...';
        if (videoUrl) return 'Video ready';
        if (videoError) return videoError || 'Video unavailable';
        return '';
    };

    return (
        <Layout>
            <div className="max-w-5xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-10"
                >
                    <motion.div
                        animate={{ rotate: [0, 5, -5, 0] }}
                        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                        className="inline-block mb-4"
                    >
                        <span className="text-6xl">👨‍🍳</span>
                    </motion.div>
                    <h1 className="text-4xl md:text-5xl font-bold font-display text-gradient-christmas mb-3">
                        What are you craving?
                    </h1>
                    <p className="text-slate-400 text-lg">
                        <Sparkles size={16} className="inline text-gold-400 mr-1" />
                        Let AI craft the perfect recipe from your pantry
                        <Sparkles size={16} className="inline text-gold-400 ml-1" />
                    </p>
                </motion.div>

                {/* Input Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="card-premium p-6 md:p-8 mb-8"
                >
                    <h2 className="text-xl font-bold text-white mb-6">What would you like to cook?</h2>

                    <div className="space-y-5">
                        {/* Servings */}
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                <Utensils size={14} className="inline mr-2" />
                                Number of Servings
                            </label>
                            <select
                                value={servings}
                                onChange={(e) => setServings(parseInt(e.target.value))}
                                className="input-field-dark"
                            >
                                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(num => (
                                    <option key={num} value={num}>{num} {num === 1 ? 'serving' : 'servings'}</option>
                                ))}
                            </select>
                        </div>

                        {/* Query Input */}
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                <ChefHat size={14} className="inline mr-2" />
                                Describe your recipe
                            </label>
                            <div className="flex gap-3">
                                <input
                                    type="text"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    onKeyPress={(e) => e.key === 'Enter' && handleGenerate()}
                                    placeholder="e.g., Quick pasta dinner, Healthy breakfast..."
                                    className="input-field-dark flex-1"
                                />
                                <motion.button
                                    onClick={handleGenerate}
                                    disabled={loading || !query.trim()}
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    className="btn-primary flex items-center gap-2 px-6"
                                >
                                    <Send size={18} />
                                    <span className="hidden sm:inline">Generate</span>
                                </motion.button>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Error State */}
                <AnimatePresence>
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400"
                        >
                            <AlertCircle size={20} />
                            <span>{error}</span>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Warning */}
                <AnimatePresence>
                    {warning && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="mb-6 p-4 bg-gold-500/10 border border-gold-500/20 rounded-xl flex items-center gap-3 text-gold-400"
                        >
                            <AlertCircle size={20} />
                            <span>{warning}</span>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Comparison Modal */}
                <AnimatePresence>
                    {comparisonMode && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center px-4"
                        >
                            <motion.div
                                initial={{ scale: 0.95, y: 20 }}
                                animate={{ scale: 1, y: 0 }}
                                exit={{ scale: 0.95, y: 20 }}
                                className="glass-panel-solid rounded-3xl shadow-2xl max-w-6xl w-full p-6 md:p-8 border border-white/10 max-h-[90vh] overflow-y-auto"
                            >
                                <div className="flex items-start justify-between mb-6">
                                    <div>
                                        <p className="text-sm font-semibold text-primary-400 uppercase tracking-wide mb-1">
                                            <Sparkles size={14} className="inline mr-1" />
                                            Preference Check
                                        </p>
                                        <h3 className="text-2xl font-bold text-white">Which recipe do you prefer?</h3>
                                        <p className="text-slate-400 mt-1">Select your favorite to personalize future recipes</p>
                                    </div>
                                </div>

                                <div className="grid md:grid-cols-2 gap-4 mb-6">
                                    {renderVariantCard(comparisonData.variantA, 'A')}
                                    {renderVariantCard(comparisonData.variantB, 'B')}
                                </div>

                                {comparisonError && (
                                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                                        {comparisonError}
                                    </div>
                                )}

                                <div className="flex flex-col md:flex-row justify-end gap-3">
                                    <button
                                        onClick={handleSkipComparison}
                                        disabled={skipSubmitting || choiceSubmitting}
                                        className="btn-secondary disabled:opacity-50"
                                    >
                                        {skipSubmitting ? 'Skipping...' : 'Skip & Generate New'}
                                    </button>
                                    <button
                                        onClick={handleConfirmChoice}
                                        disabled={!selectedVariant || choiceSubmitting || skipSubmitting}
                                        className="btn-primary disabled:opacity-50"
                                    >
                                        {choiceSubmitting ? 'Saving...' : selectedVariant ? `Choose ${selectedVariant}` : 'Select a variant'}
                                    </button>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Premium Loading */}
                <AnimatePresence>
                    {loading && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center py-20"
                        >
                            <div className="relative mb-8">
                                <motion.div
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                                    className="w-32 h-32 rounded-full border-4 border-primary-500/30 border-t-primary-500 flex items-center justify-center"
                                >
                                    <span className="text-6xl">🍳</span>
                                </motion.div>
                                <motion.div
                                    animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.2, 0.5] }}
                                    transition={{ duration: 2, repeat: Infinity }}
                                    className="absolute inset-0 -m-4 rounded-full border-2 border-gold-400/30"
                                />
                            </div>
                            <motion.p
                                animate={{ opacity: [1, 0.5, 1] }}
                                transition={{ duration: 1.5, repeat: Infinity }}
                                className="text-xl font-semibold text-gradient mb-2"
                            >
                                Crafting your perfect recipe...
                            </motion.p>
                            <p className="text-slate-500">For {servings} {servings === 1 ? 'serving' : 'servings'} • This may take 15-30 seconds</p>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Recipe Display */}
                <AnimatePresence>
                    {recipe && !loading && isRecipeError(recipe) && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 20 }}
                            className="card-premium p-8 text-center"
                        >
                            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gold-500/20 flex items-center justify-center">
                                <AlertCircle size={40} className="text-gold-400" />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-3">
                                Couldn't Generate Recipe
                            </h3>
                            <p className="text-slate-400 max-w-md mx-auto mb-6">
                                Sorry, we couldn't create a recipe for "{query}" with your current ingredients.
                                Try a different request or add more items to your pantry!
                            </p>
                            <div className="flex gap-3 justify-center">
                                <button
                                    onClick={() => { setRecipe(null); setQuery(''); }}
                                    className="btn-secondary"
                                >
                                    Try Something Else
                                </button>
                                <button
                                    onClick={() => { setRecipe(null); handleGenerate(); }}
                                    className="btn-primary"
                                >
                                    <Sparkles size={16} className="inline mr-2" />
                                    Try Again
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {recipe && !loading && !isRecipeError(recipe) && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 20 }}
                            className="card-premium overflow-hidden"
                        >
                            {/* Recipe Header */}
                            <div className="bg-gradient-to-r from-secondary-800 to-secondary-900 p-6 border-b border-white/5">
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div>
                                        <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
                                            {recipe.recipe?.name || recipe.name || "Generated Recipe"}
                                        </h2>
                                        <div className="flex gap-2 flex-wrap">
                                            {recipe.recipe?.cuisine && (
                                                <span className="badge-gold">🍽️ {recipe.recipe.cuisine}</span>
                                            )}
                                            {recipe.recipe?.time && (
                                                <span className="badge-frost flex items-center gap-1">
                                                    <Clock size={12} />
                                                    {recipe.recipe.time}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <motion.button
                                            onClick={() => handleFeedback(2)}
                                            whileHover={{ scale: 1.1 }}
                                            whileTap={{ scale: 0.9 }}
                                            className={`p-3 rounded-xl transition-all duration-300 ${feedback === 2
                                                ? 'bg-evergreen-500/20 text-evergreen-400 shadow-lg'
                                                : 'bg-secondary-700/50 text-slate-400 hover:text-evergreen-400 hover:bg-evergreen-500/10'
                                                }`}
                                        >
                                            <ThumbsUp size={20} />
                                        </motion.button>
                                        <motion.button
                                            onClick={() => handleFeedback(1)}
                                            whileHover={{ scale: 1.1 }}
                                            whileTap={{ scale: 0.9 }}
                                            className={`p-3 rounded-xl transition-all duration-300 ${feedback === 1
                                                ? 'bg-red-500/20 text-red-400 shadow-lg'
                                                : 'bg-secondary-700/50 text-slate-400 hover:text-red-400 hover:bg-red-500/10'
                                                }`}
                                        >
                                            <ThumbsDown size={20} />
                                        </motion.button>
                                    </div>
                                </div>
                            </div>

                            {/* Recipe Content */}
                            <div className="p-6 md:p-8 grid md:grid-cols-3 gap-8">
                                {/* Ingredients */}
                                <div className="md:col-span-1 space-y-6">
                                    <div>
                                        <h3 className="font-bold text-lg text-white mb-4 flex items-center gap-2">
                                            <span className="w-8 h-8 bg-primary-500/20 rounded-lg flex items-center justify-center text-primary-400">🥘</span>
                                            Ingredients
                                        </h3>
                                        <ul className="space-y-2">
                                            {(recipe.recipe?.main_ingredients || recipe.main_ingredients || []).map((ing, i) => {
                                                const ingNorm = normalizeName(ing);
                                                const invItem = inventory.find((item) => {
                                                    const invNorm = normalizeName(item.item_name);
                                                    return invNorm && ingNorm && (invNorm.includes(ingNorm) || ingNorm.includes(invNorm));
                                                });
                                                const needsRefill = invItem && Number(invItem.quantity) <= LOW_STOCK_THRESHOLD;
                                                const missing = !invItem;
                                                return (
                                                    <motion.li
                                                        key={i}
                                                        initial={{ opacity: 0, x: -10 }}
                                                        animate={{ opacity: 1, x: 0 }}
                                                        transition={{ delay: i * 0.05 }}
                                                        className="text-slate-300 flex items-start gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors"
                                                    >
                                                        <span className="w-2 h-2 rounded-full bg-primary-500 mt-2 shrink-0" />
                                                        <span className="flex-1">{ing}</span>
                                                        {needsRefill && (
                                                            <span className="badge bg-gold-500/20 text-gold-400 border border-gold-500/30 text-xs">
                                                                Low
                                                            </span>
                                                        )}
                                                        {missing && (
                                                            <span className="badge bg-red-500/20 text-red-400 border border-red-500/30 text-xs">
                                                                Missing
                                                            </span>
                                                        )}
                                                    </motion.li>
                                                );
                                            })}
                                        </ul>
                                    </div>

                                    {(recipe.missing_ingredients?.length > 0) && (
                                        <div className="bg-red-500/10 p-4 rounded-xl border border-red-500/20">
                                            <h3 className="font-bold text-red-400 mb-3 text-sm flex items-center gap-2">
                                                <AlertCircle size={16} />
                                                Missing Items
                                            </h3>
                                            <ul className="space-y-1">
                                                {recipe.missing_ingredients.map((ing, i) => (
                                                    <li key={i} className="text-red-300 text-sm flex items-center gap-2">
                                                        • {ing}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>

                                {/* Steps */}
                                <div className="md:col-span-2">
                                    <h3 className="font-bold text-lg text-white mb-4 flex items-center gap-2">
                                        <span className="w-8 h-8 bg-gold-500/20 rounded-lg flex items-center justify-center text-gold-400">📝</span>
                                        Instructions
                                    </h3>
                                    <div className="space-y-3">
                                        {(() => {
                                            const stepsToRender = recipe.parsedSteps?.length
                                                ? recipe.parsedSteps
                                                : parseSteps(recipe.raw_text || recipe.recipe?.steps || recipe.steps || '');

                                            if (!stepsToRender.length && recipe.raw_text) {
                                                return (
                                                    <div className="glass-frost p-6 rounded-xl">
                                                        <p className="whitespace-pre-line text-slate-300 leading-relaxed">{recipe.raw_text}</p>
                                                    </div>
                                                );
                                            }

                                            return stepsToRender.map((step, i) => (
                                                <motion.div
                                                    key={i}
                                                    initial={{ opacity: 0, y: 12 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    transition={{ delay: i * 0.08 }}
                                                    className="relative overflow-hidden rounded-xl border border-white/5 bg-secondary-800/50 hover:bg-secondary-800/70 transition-all duration-200 group"
                                                >
                                                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-primary-500 to-gold-500 opacity-50 group-hover:opacity-100 transition-opacity" />
                                                    <div className="p-4 pl-5 flex gap-4">
                                                        <div className="flex-shrink-0">
                                                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-600 to-gold-500 text-white font-bold flex items-center justify-center shadow-lg text-sm">
                                                                {i + 1}
                                                            </div>
                                                        </div>
                                                        <div className="flex-1">
                                                            <p className="text-slate-200 leading-relaxed">{step}</p>
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            ));
                                        })()}
                                    </div>

                                    {/* Actions */}
                                    <div className="mt-8 pt-6 border-t border-white/5 flex flex-col sm:flex-row justify-end gap-3">
                                        <motion.button
                                            onClick={() => setShowVideoModal(true)}
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                            className="btn-gold flex items-center justify-center gap-2"
                                        >
                                            <Play size={18} />
                                            Generate Video
                                        </motion.button>
                                        <motion.button
                                            onClick={handleCooked}
                                            disabled={cooked}
                                            whileHover={{ scale: cooked ? 1 : 1.02 }}
                                            whileTap={{ scale: cooked ? 1 : 0.98 }}
                                            className={`flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all ${cooked
                                                ? 'bg-evergreen-500/20 text-evergreen-400 cursor-default border border-evergreen-500/30'
                                                : 'btn-primary'
                                                }`}
                                        >
                                            {cooked ? (
                                                <>
                                                    <CheckCircle size={18} />
                                                    Marked as Cooked
                                                </>
                                            ) : (
                                                <>
                                                    <ChefHat size={18} />
                                                    I Cooked This
                                                </>
                                            )}
                                        </motion.button>
                                    </div>

                                    {/* Video Preview */}
                                    {(videoGenerating || videoUrl || videoError) && (
                                        <div className="mt-6 glass-frost rounded-xl p-4">
                                            <div className="flex items-center justify-between mb-3">
                                                <p className="text-sm font-semibold text-white">Video Preview</p>
                                                <div className="flex items-center gap-2">
                                                    <p className="text-xs text-slate-400">{videoStatusLabel()}</p>
                                                    {videoGenerating && <Loader2 className="animate-spin text-primary-500" size={16} />}
                                                </div>
                                            </div>
                                            {videoGenerating && (
                                                <div className="w-full bg-secondary-800 rounded-full h-2 overflow-hidden mb-3">
                                                    <motion.div
                                                        className="h-full bg-gradient-to-r from-primary-500 to-gold-500"
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${videoProgress}%` }}
                                                        transition={{ duration: 0.3 }}
                                                    />
                                                </div>
                                            )}
                                            {videoUrl && (
                                                <div className="rounded-xl overflow-hidden border border-white/10 bg-black">
                                                    <video src={videoUrl} controls className="w-full max-h-80" />
                                                </div>
                                            )}
                                            {videoError && (
                                                <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                                                    {videoError}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    <p className="mt-4 text-xs text-slate-500">
                                        Note: Your dietary preferences may affect the AI's response.
                                    </p>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Video Confirmation Modal */}
            <AnimatePresence>
                {showVideoModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="modal-overlay"
                        onClick={() => setShowVideoModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="modal-content"
                        >
                            <div className="modal-header">
                                <div className="flex items-center gap-3">
                                    <div className="w-12 h-12 rounded-xl bg-gold-500/20 text-gold-400 flex items-center justify-center">
                                        <Play size={24} />
                                    </div>
                                    <div>
                                        <h3 className="text-xl font-bold text-white">Generate Cooking Video?</h3>
                                        <p className="text-slate-400 text-sm">
                                            Create a walkthrough for "{recipe?.recipe?.name || recipe?.name || 'this recipe'}"
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <div className="modal-body">
                                <div className="glass-frost rounded-xl p-4 text-sm text-slate-300">
                                    <p className="font-semibold text-white mb-1">What happens next</p>
                                    <p>We'll start generation and show the video when it's ready.</p>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button onClick={() => setShowVideoModal(false)} className="btn-secondary">
                                    Cancel
                                </button>
                                <button onClick={handleVideoConfirm} className="btn-gold">
                                    <Sparkles size={16} className="inline mr-1" />
                                    Start Generation
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </Layout>
    );
};

export default RecipeGenerator;
