import React, { useRef, useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Send, ThumbsUp, ThumbsDown, CheckCircle, Loader2, Sparkles, ChefHat, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const RecipeGenerator = () => {
    const [query, setQuery] = useState('');
    const [servings, setServings] = useState(2);
    const [loading, setLoading] = useState(false);
    const [recipe, setRecipe] = useState(null);
    const [historyId, setHistoryId] = useState(null);
    const [feedback, setFeedback] = useState(null); // 1 or 2
    const [cooked, setCooked] = useState(false);
    const [error, setError] = useState('');
    const [comparisonMode, setComparisonMode] = useState(false);
    const [comparisonData, setComparisonData] = useState({ variantA: null, variantB: null });
    const [preferenceId, setPreferenceId] = useState(null);
    const [selectedVariant, setSelectedVariant] = useState(null); // "A" | "B"
    const [choiceSubmitting, setChoiceSubmitting] = useState(false);
    const [skipSubmitting, setSkipSubmitting] = useState(false);
    const [comparisonError, setComparisonError] = useState('');
    const [inventory, setInventory] = useState([]);
    const [warning, setWarning] = useState('');
    const LOW_STOCK_THRESHOLD = 0.1; // treat near-zero as out of stock

    // Video generation (mock-ready, flag-gated)
    const [showVideoModal, setShowVideoModal] = useState(false);
    const [videoGenerating, setVideoGenerating] = useState(false);
    const [videoProgress, setVideoProgress] = useState(0);
    const [videoUrl, setVideoUrl] = useState('');
    const [videoError, setVideoError] = useState('');
    const progressTimerRef = useRef(null);
    const VIDEO_MOCK_URL = 'https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'; // lightweight sample for mock mode

    React.useEffect(() => () => cleanupProgressTimer(), []);

    const parseSteps = (steps) => {
        // Normalize steps into an array for consistent rendering
        if (Array.isArray(steps)) {
            return steps.map((s) => (typeof s === 'string' ? s.trim() : '')).filter(Boolean);
        }
        if (typeof steps !== 'string') return [];

        const cleaned = steps.replace(/\r/g, '').trim();
        if (!cleaned) return [];

        // Helper: split when "Step 1.", "Step 2." markers appear anywhere (not just newlines)
        const splitByMarkers = (text) => {
            const markers = [...text.matchAll(/step\s*\d+[\.:\-]?\s*/gi)];
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
        if (stepParts.length) {
            return stepParts;
        }

        // Bullet list (lines starting with "- " or "* ")
        const bulletMatches = cleaned.match(/^\s*[-*]\s+/m);
        if (bulletMatches) {
            return cleaned
                .split(/\n+/)
                .map((line) => line.replace(/^\s*[-*]\s+/, '').trim())
                .filter(Boolean);
        }

        // If the model used "Step 1." with newlines, split on line-based markers
        const stepRegex = /(?:^|\n)\s*Step\s*\d+[\.\:\-\s]*/gi;
        if (cleaned.match(stepRegex)) {
            return cleaned
                .split(stepRegex)
                .map((s) => s.trim())
                .filter(Boolean);
        }

        // Fallback: split on newlines or sentences
        return cleaned
            .split(/\n+/)
            .flatMap((chunk) => chunk.split(/(?<=[\.!?])\s+/))
            .map((s) => s.trim())
            .filter(Boolean);
    };

    const parseRecipeResponse = (content) => {
        // Handle various response formats and surface parsed steps
        let parsed = { raw_text: 'Unable to parse recipe' };

        if (typeof content === 'object' && content !== null) {
            parsed = content;
        } else if (typeof content === 'string') {
            try {
                // 1. Try to find JSON inside markdown code blocks first
                const codeBlockMatch = content.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
                if (codeBlockMatch) {
                    parsed = JSON.parse(codeBlockMatch[1]);
                } else {
                    // 2. Fallback: Find the first valid JSON object in the text
                    const firstOpen = content.indexOf('{');
                    if (firstOpen !== -1) {
                        // Try to find the matching closing brace by counting
                        let balance = 0;
                        let lastClose = -1;
                        let inString = false;
                        let escape = false;

                        for (let i = firstOpen; i < content.length; i++) {
                            const char = content[i];

                            if (escape) {
                                escape = false;
                                continue;
                            }

                            if (char === '\\') {
                                escape = true;
                                continue;
                            }

                            if (char === '"') {
                                inString = !inString;
                                continue;
                            }

                            if (!inString) {
                                if (char === '{') {
                                    balance++;
                                } else if (char === '}') {
                                    balance--;
                                    if (balance === 0) {
                                        lastClose = i;
                                        break;
                                    }
                                }
                            }
                        }

                        if (lastClose !== -1) {
                            try {
                                parsed = JSON.parse(content.substring(firstOpen, lastClose + 1));
                            } catch (e) {
                                // If that fails, try the greedy match as a last resort (though unlikely to help if balanced failed)
                                const jsonMatch = content.match(/\{[\s\S]*\}/);
                                if (jsonMatch) {
                                    try {
                                        parsed = JSON.parse(jsonMatch[0]);
                                    } catch {
                                        parsed = { raw_text: content };
                                    }
                                } else {
                                    parsed = { raw_text: content };
                                }
                            }
                        } else {
                            // No balanced closing brace found, try greedy
                            const jsonMatch = content.match(/\{[\s\S]*\}/);
                            if (jsonMatch) {
                                try {
                                    parsed = JSON.parse(jsonMatch[0]);
                                } catch {
                                    parsed = { raw_text: content };
                                }
                            } else {
                                parsed = { raw_text: content };
                            }
                        }
                    } else {
                        parsed = { raw_text: content };
                    }
                }
            } catch {
                parsed = { raw_text: content };
            }
        }

        const recipeNode = parsed.recipe || parsed;
        const stepsFromRecipe = parseSteps(recipeNode.steps);
        const stepsFromRaw = stepsFromRecipe.length ? stepsFromRecipe : parseSteps(parsed.raw_text || '');

        return {
            ...parsed,
            parsedSteps: stepsFromRecipe.length ? stepsFromRecipe : stepsFromRaw,
        };
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
            <button
                type="button"
                onClick={() => setSelectedVariant(label)}
                className={`flex-1 text-left bg-white border rounded-2xl p-5 shadow-sm transition-all ${
                    isSelected ? 'border-primary-500 ring-4 ring-primary-100 scale-[1.01]' : 'border-slate-200 hover:border-primary-200'
                }`}
            >
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <span className="px-3 py-1 rounded-full text-sm font-semibold bg-primary-50 text-primary-700 border border-primary-100">{label}</span>
                        <h3 className="text-xl font-bold text-slate-900">{title}</h3>
                    </div>
                    {isSelected && <CheckCircle className="text-primary-600" size={20} />}
                </div>
                <div className="flex gap-2 flex-wrap mb-4">
                    {cuisine && <span className="badge-accent">🍽️ {cuisine}</span>}
                    {time && <span className="badge-primary">⏱️ {time}</span>}
                </div>
                <div className="space-y-3">
                    <div>
                        <h4 className="font-semibold text-slate-800 mb-2">Ingredients</h4>
                        <ul className="space-y-1 text-slate-700 text-sm max-h-28 overflow-y-auto">
                            {ingredients.map((ing, idx) => (
                                <li key={idx}>• {typeof ing === 'string' ? ing : ing?.name || JSON.stringify(ing)}</li>
                            ))}
                        </ul>
                    </div>
                    <div>
                        <h4 className="font-semibold text-slate-800 mb-2">Instructions</h4>
                        <ul className="space-y-1 text-slate-700 text-sm max-h-32 overflow-y-auto">
                            {steps.length ? steps.map((s, i) => <li key={i}>• {s}</li>) : <li className="text-slate-400">Steps not provided</li>}
                        </ul>
                    </div>
                </div>
            </button>
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
        // Prefetch inventory to tag depleted items and validate requests
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
                // refresh inventory to catch latest quantities
                fetchInventory();

                // Warn if requested protein not in inventory
                const maybeProtein = query.toLowerCase();
                const lacksChicken = maybeProtein.includes('chicken') && !hasInventoryItem('chicken');
                const lacksMain = (recipeData.recipe?.main_ingredients || []).some(
                    (ing) => !hasInventoryItem(ing)
                );
                if (lacksChicken || lacksMain) {
                    setWarning('Your inventory may be missing some ingredients (e.g., chicken); please verify before cooking.');
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
            await handleGenerate(); // auto-regenerate a single recipe
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
        } catch (err) {
            console.error(err);
        }
    };

    const handleCooked = async () => {
        if (!historyId) return;
        try {
            await api.post(`/recipes/${historyId}/cooked`);
            setCooked(true);
            await fetchInventory();
        } catch (err) {
            console.error(err);
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
            const prompt =
                recipe?.recipe?.name ||
                recipe?.name ||
                (query ? `Cooking video for: ${query}` : 'Cooking video');

            // lightweight progress simulation while backend works
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
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center mb-10"
                >
                    <h1 className="text-5xl font-bold text-gradient mb-4">
                        What are you craving?
                    </h1>
                    <p className="text-slate-500 text-lg">
                        Let AI craft the perfect recipe from your pantry.
                    </p>
                </motion.div>

                {/* Search Bar */}
                {/* Input Section with Servings */}
                <div className="bg-white rounded-2xl shadow-lg p-8 border border-slate-200 mb-8">
                    <h2 className="text-2xl font-bold text-slate-900 mb-6">What would you like to cook?</h2>

                    <div className="space-y-4">
                        {/* Servings Dropdown */}
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Number of Servings
                            </label>
                            <select
                                value={servings}
                                onChange={(e) => setServings(parseInt(e.target.value))}
                                className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-primary-500 focus:ring-4 focus:ring-primary-100 outline-none transition-all bg-white"
                            >
                                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(num => (
                                    <option key={num} value={num}>{num} {num === 1 ? 'serving' : 'servings'}</option>
                                ))}
                            </select>
                        </div>

                        {/* Recipe Query Input */}
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Describe your recipe
                            </label>
                            <div className="flex gap-3">
                                <input
                                    type="text"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    onKeyPress={(e) => e.key === 'Enter' && handleGenerate()}
                                    placeholder="e.g., Quick pasta dinner, Healthy breakfast..."
                                    className="flex-1 px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-primary-500 focus:ring-4 focus:ring-primary-100 outline-none transition-all"
                                />
                                <button
                                    onClick={handleGenerate}
                                    disabled={loading || !query.trim()}
                                    className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <Send size={20} />
                                    Generate
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Error State */}
                <AnimatePresence>
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700"
                        >
                            <AlertCircle size={20} />
                            <span>{error}</span>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Warnings */}
                <AnimatePresence>
                    {warning && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-3 text-amber-800"
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
                            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center px-4"
                        >
                            <motion.div
                                initial={{ scale: 0.95, y: 20 }}
                                animate={{ scale: 1, y: 0 }}
                                exit={{ scale: 0.95, y: 20 }}
                                className="bg-white rounded-3xl shadow-2xl max-w-6xl w-full p-6 border border-slate-200"
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <p className="text-sm font-semibold text-primary-600 uppercase tracking-wide">Preference Check</p>
                                        <h3 className="text-2xl font-bold text-slate-900">Which recipe do you prefer?</h3>
                                        <p className="text-slate-500 mt-1">Select your favorite so we can personalize future recipes. Every 7th generation shows this comparison.</p>
                                    </div>
                                    <Sparkles className="text-primary-500" />
                                </div>

                                <div className="grid md:grid-cols-2 gap-4">
                                    {renderVariantCard(comparisonData.variantA, 'A')}
                                    {renderVariantCard(comparisonData.variantB, 'B')}
                                </div>

                                {comparisonError && (
                                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700">
                                        {comparisonError}
                                    </div>
                                )}

                                <div className="mt-6 flex flex-col md:flex-row justify-end gap-3">
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
                                        {choiceSubmitting ? 'Saving choice...' : selectedVariant ? `Choose Variant ${selectedVariant}` : 'Select a variant'}
                                    </button>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Premium Loading with Spinning Chef Hat */}
                <AnimatePresence>
                    {loading && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center py-20"
                        >
                            <div className="relative">
                                <motion.div
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                    className="text-8xl"
                                >
                                    👨‍🍳
                                </motion.div>
                                <motion.div
                                    animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.2, 0.5] }}
                                    transition={{ duration: 2, repeat: Infinity }}
                                    className="absolute inset-0 -m-4 rounded-full border-4 border-primary-400"
                                />
                            </div>
                            <motion.p
                                animate={{ opacity: [1, 0.5, 1] }}
                                transition={{ duration: 1.5, repeat: Infinity }}
                                className="mt-8 text-xl font-semibold bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent"
                            >
                                Crafting your perfect recipe for {servings} {servings === 1 ? 'serving' : 'servings'}...
                            </motion.p>
                            <p className="mt-2 text-slate-500">This may take 15-30 seconds</p>
                        </motion.div>
                    )}
                </AnimatePresence>


                {/* Recipe Display */}
                <AnimatePresence>
                    {recipe && !loading && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 20 }}
                            className="card-premium overflow-hidden"
                        >
                            {/* Header */}
                            <div className="bg-gradient-to-r from-slate-50 to-white p-6 border-b border-slate-200 flex justify-between items-start">
                                <div>
                                    <h2 className="text-3xl font-bold text-slate-900 mb-2">
                                        {recipe.recipe?.name || recipe.name || "Generated Recipe"}
                                    </h2>
                                    <div className="flex gap-2 flex-wrap">
                                        {recipe.recipe?.cuisine && (
                                            <span className="badge-accent">
                                                🍽️ {recipe.recipe.cuisine}
                                            </span>
                                        )}
                                        {recipe.recipe?.time && (
                                            <span className="badge-primary">
                                                ⏱️ {recipe.recipe.time}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => handleFeedback(2)}
                                        className={`p-3 rounded-xl transition-all duration-300 ${feedback === 2
                                            ? 'bg-success-100 text-success-600 shadow-lg scale-110'
                                            : 'hover:bg-slate-100 text-slate-400 hover:text-success-600'
                                            }`}
                                    >
                                        <ThumbsUp size={20} />
                                    </button>
                                    <button
                                        onClick={() => handleFeedback(1)}
                                        className={`p-3 rounded-xl transition-all duration-300 ${feedback === 1
                                            ? 'bg-red-100 text-red-600 shadow-lg scale-110'
                                            : 'hover:bg-slate-100 text-slate-400 hover:text-red-600'
                                            }`}
                                    >
                                        <ThumbsDown size={20} />
                                    </button>
                                </div>
                            </div>

                            {/* Content */}
                            <div className="p-8 grid md:grid-cols-3 gap-8">
                                {/* Ingredients */}
                                <div className="md:col-span-1 space-y-6">
                                    <div>
                                        <h3 className="font-bold text-lg text-slate-900 mb-4 flex items-center gap-2">
                                            <span className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center text-primary-600">🥘</span>
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
                                                    <li key={i} className="text-slate-700 flex items-start gap-3 p-2 rounded-lg hover:bg-slate-50 transition-colors">
                                                        <span className="w-2 h-2 rounded-full bg-primary-500 mt-2 shrink-0" />
                                                        <span className="flex-1">{ing}</span>
                                                        {needsRefill && (
                                                            <span className="text-xs font-semibold text-red-600 bg-red-50 border border-red-200 px-2 py-1 rounded-lg">
                                                                Refill
                                                            </span>
                                                        )}
                                                        {missing && (
                                                            <span className="text-xs font-semibold text-red-600 bg-red-50 border border-red-200 px-2 py-1 rounded-lg">
                                                                Missing
                                                            </span>
                                                        )}
                                                    </li>
                                                );
                                            })}
                                        </ul>
                                    </div>

                                    {(recipe.missing_ingredients?.length > 0) && (
                                        <div className="bg-red-50 p-4 rounded-xl border-2 border-red-100">
                                            <h3 className="font-bold text-red-700 mb-3 text-sm flex items-center gap-2">
                                                <AlertCircle size={16} />
                                                Missing Items
                                            </h3>
                                            <ul className="space-y-1">
                                                {recipe.missing_ingredients.map((ing, i) => (
                                                    <li key={i} className="text-red-600 text-sm flex items-center gap-2">
                                                        • {ing}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>

                                {/* Steps */}
                                <div className="md:col-span-2">
                                    <h3 className="font-bold text-lg text-slate-900 mb-4 flex items-center gap-2">
                                        <span className="w-8 h-8 bg-accent-100 rounded-lg flex items-center justify-center text-accent-600">📝</span>
                                        Instructions
                                    </h3>
                                    <div className="space-y-4">
                                        {(() => {
                                            const stepsToRender = recipe.parsedSteps?.length
                                                ? recipe.parsedSteps
                                                : parseSteps(recipe.raw_text || recipe.recipe?.steps || recipe.steps || '');

                                            if (!stepsToRender.length && recipe.raw_text) {
                                                return (
                                                    <div className="bg-gradient-to-br from-slate-50 to-white p-6 rounded-xl border-2 border-slate-200 shadow-sm">
                                                        <p className="whitespace-pre-line text-slate-700 leading-relaxed">{recipe.raw_text}</p>
                                                    </div>
                                                );
                                            }

                                            return (
                                                <div className="grid grid-cols-1 gap-4">
                                                    {stepsToRender.map((step, i) => (
                                                        <motion.div
                                                            key={i}
                                                            initial={{ opacity: 0, y: 12 }}
                                                            animate={{ opacity: 1, y: 0 }}
                                                            transition={{ delay: i * 0.08 }}
                                                            className="relative overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm hover:shadow-lg transition-all duration-200 group"
                                                        >
                                                            <div className="absolute -left-10 -top-10 w-28 h-28 bg-gradient-to-br from-accent-100 to-primary-100 rounded-full blur-2xl opacity-70 group-hover:opacity-90 transition-opacity" />
                                                            <div className="relative p-5 flex gap-4">
                                                                <div className="flex-shrink-0">
                                                                    <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary-600 to-accent-500 text-white font-bold flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                                                                        {i + 1}
                                                                    </div>
                                                                </div>
                                                                <div className="flex-1">
                                                                    <p className="text-slate-800 leading-relaxed">{step}</p>
                                                                </div>
                                                            </div>
                                                        </motion.div>
                                                    ))}
                                                </div>
                                            );
                                        })()}
                                    </div>

                                    {/* Actions */}
                                    <div className="mt-8 pt-6 border-t border-slate-200 flex justify-end gap-3">
                                        <button
                                            onClick={() => setShowVideoModal(true)}
                                            className="flex items-center gap-3 px-8 py-4 rounded-xl font-semibold transition-all duration-300 bg-gradient-to-r from-accent-600 to-accent-500 hover:from-accent-500 hover:to-accent-400 text-white shadow-lg hover:shadow-xl transform hover:scale-[1.02] active:scale-[0.98]"
                                        >
                                            <Sparkles size={22} />
                                            Generate Video
                                        </button>
                                        <button
                                            onClick={handleCooked}
                                            disabled={cooked}
                                            className={`flex items-center gap-3 px-8 py-4 rounded-xl font-semibold transition-all duration-300 ${cooked
                                                ? 'bg-success-100 text-success-700 cursor-default'
                                                : 'bg-gradient-to-r from-slate-900 to-slate-700 text-white hover:from-slate-800 hover:to-slate-600 shadow-lg hover:shadow-xl transform hover:scale-[1.02] active:scale-[0.98]'
                                                }`}
                                        >
                                            {cooked ? (
                                                <>
                                                    <CheckCircle size={22} />
                                                    Marked as Cooked
                                                </>
                                            ) : (
                                                <>
                                                    <ChefHat size={22} />
                                                    I Cooked This
                                                </>
                                            )}
                                        </button>
                                    </div>
                                    {/* Video Preview / Streaming */}
                                    {(videoGenerating || videoUrl || videoError) && (
                                        <div className="mt-6 border border-dashed border-slate-200 rounded-2xl p-4 bg-slate-50">
                                            <div className="flex items-center justify-between mb-3">
                                                <p className="text-sm font-semibold text-slate-800">Video preview</p>
                                                <p className="text-xs text-slate-500">{videoStatusLabel()}</p>
                                                {videoGenerating && <Loader2 className="animate-spin text-primary-500" size={18} />}
                                            </div>
                                            {videoGenerating && (
                                                <div className="w-full bg-white rounded-xl border border-slate-200 h-3 overflow-hidden mb-3">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-primary-500 to-accent-500 transition-all duration-200"
                                                        style={{ width: `${videoProgress}%` }}
                                                    />
                                                </div>
                                            )}
                                            {videoUrl && (
                                                <div className="rounded-xl overflow-hidden border border-slate-200 bg-black">
                                                    <video src={videoUrl} controls className="w-full max-h-96" />
                                                </div>
                                            )}
                                            {videoError && (
                                                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                                                    {videoError}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    <p className="mt-4 text-xs text-slate-500">
                                        Note: Your dietary preferences may affect the AI’s response.
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
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
                        onClick={() => setShowVideoModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 border border-slate-200"
                        >
                            <div className="flex items-start gap-3 mb-4">
                                <div className="w-10 h-10 rounded-xl bg-accent-100 text-accent-600 flex items-center justify-center">
                                    <Sparkles size={20} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-slate-900">Generate cooking video?</h3>
                                    <p className="text-slate-600 text-sm mt-1">
                                        We’ll create a short walkthrough for “{recipe?.recipe?.name || recipe?.name || 'this recipe'}”.
                                    </p>
                                </div>
                            </div>

                            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm text-slate-600 mb-4">
                                <p className="font-semibold text-slate-800 mb-1">What happens next</p>
                                <p>We start generation and show the video when it is ready.</p>
                            </div>

                            <div className="flex justify-end gap-3">
                                <button onClick={() => setShowVideoModal(false)} className="btn-secondary">
                                    Cancel
                                </button>
                                <button
                                    onClick={handleVideoConfirm}
                                    className="btn-primary bg-gradient-to-r from-accent-600 to-accent-500 hover:from-accent-500 hover:to-accent-400"
                                >
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
