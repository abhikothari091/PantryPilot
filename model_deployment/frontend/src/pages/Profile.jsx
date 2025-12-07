import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Save, Loader2, Check, Sparkles, Heart, Globe, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '../components/Toast';
import { SkeletonProfileForm } from '../components/Skeleton';

const Profile = () => {
    const toast = useToast();
    const [profile, setProfile] = useState({
        dietary_restrictions: [],
        allergies: [],
        favorite_cuisines: []
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const res = await api.get('/users/profile');
                setProfile({
                    dietary_restrictions: res.data.dietary_restrictions || [],
                    allergies: res.data.allergies || [],
                    favorite_cuisines: res.data.favorite_cuisines || []
                });
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchProfile();
    }, []);

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            await api.put('/users/profile', profile);
            toast.success('Preferences saved!');
        } catch (err) {
            console.error(err);
            toast.error('Failed to save preferences');
        } finally {
            setSaving(false);
        }
    };

    const toggleItem = (field, value) => {
        setProfile(prev => {
            const list = prev[field];
            if (list.includes(value)) {
                return { ...prev, [field]: list.filter(item => item !== value) };
            } else {
                return { ...prev, [field]: [...list, value] };
            }
        });
    };

    const DIETARY_OPTIONS = [
        { value: 'Vegan', emoji: '🌱' },
        { value: 'Vegetarian', emoji: '🥗' },
        { value: 'Gluten-Free', emoji: '🌾' },
        { value: 'Dairy-Free', emoji: '🥛' },
        { value: 'Keto', emoji: '🥑' },
        { value: 'Paleo', emoji: '🍖' },
    ];

    const CUISINE_OPTIONS = [
        { value: 'Italian', emoji: '🇮🇹' },
        { value: 'Chinese', emoji: '🇨🇳' },
        { value: 'Mexican', emoji: '🇲🇽' },
        { value: 'Indian', emoji: '🇮🇳' },
        { value: 'Japanese', emoji: '🇯🇵' },
        { value: 'Thai', emoji: '🇹🇭' },
        { value: 'Mediterranean', emoji: '🫒' },
        { value: 'American', emoji: '🇺🇸' },
    ];

    if (loading) {
        return (
            <Layout>
                <div className="max-w-3xl mx-auto">
                    <div className="mb-8 animate-pulse">
                        <div className="h-10 bg-secondary-700/50 rounded w-64 mb-2" />
                        <div className="h-4 bg-secondary-700/50 rounded w-96" />
                    </div>
                    <SkeletonProfileForm />
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="max-w-3xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <h1 className="text-3xl md:text-4xl font-bold font-display text-gradient mb-2">
                        My Preferences
                    </h1>
                    <p className="text-slate-400 flex items-center gap-2">
                        <Sparkles size={16} className="text-gold-400" />
                        Customize your dietary needs for personalized recommendations
                    </p>
                </motion.div>

                <motion.form
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    onSubmit={handleSave}
                    className="space-y-8"
                >
                    {/* Dietary Restrictions */}
                    <div id="section-dietary" className="card-premium p-6">
                        <div className="flex items-center gap-3 mb-5">
                            <div className="w-10 h-10 rounded-xl bg-evergreen-500/20 flex items-center justify-center">
                                <Heart size={20} className="text-evergreen-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-white">Dietary Restrictions</h3>
                                <p className="text-sm text-slate-500">Select any dietary preferences you follow</p>
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-3">
                            {DIETARY_OPTIONS.map((option, index) => {
                                const isSelected = profile.dietary_restrictions.includes(option.value);
                                return (
                                    <motion.button
                                        key={option.value}
                                        type="button"
                                        initial={{ opacity: 0, scale: 0.9 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: index * 0.03 }}
                                        onClick={() => toggleItem('dietary_restrictions', option.value)}
                                        className={`px-4 py-2.5 rounded-xl border transition-all duration-300 flex items-center gap-2 ${isSelected
                                            ? 'bg-evergreen-500/20 border-evergreen-500/50 text-evergreen-300 shadow-lg shadow-evergreen-500/10'
                                            : 'bg-secondary-800/50 border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-300'
                                            }`}
                                    >
                                        <span>{option.emoji}</span>
                                        <span className="font-medium">{option.value}</span>
                                        {isSelected && <Check size={16} className="text-evergreen-400" />}
                                    </motion.button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Favorite Cuisines */}
                    <div className="card-premium p-6">
                        <div className="flex items-center gap-3 mb-5">
                            <div className="w-10 h-10 rounded-xl bg-gold-500/20 flex items-center justify-center">
                                <Globe size={20} className="text-gold-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-white">Favorite Cuisines</h3>
                                <p className="text-sm text-slate-500">Choose cuisines you love to cook</p>
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-3">
                            {CUISINE_OPTIONS.map((option, index) => {
                                const isSelected = profile.favorite_cuisines.includes(option.value);
                                return (
                                    <motion.button
                                        key={option.value}
                                        type="button"
                                        initial={{ opacity: 0, scale: 0.9 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: index * 0.03 }}
                                        onClick={() => toggleItem('favorite_cuisines', option.value)}
                                        className={`px-4 py-2.5 rounded-xl border transition-all duration-300 flex items-center gap-2 ${isSelected
                                            ? 'bg-gold-500/20 border-gold-500/50 text-gold-300 shadow-lg shadow-gold-500/10'
                                            : 'bg-secondary-800/50 border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-300'
                                            }`}
                                    >
                                        <span>{option.emoji}</span>
                                        <span className="font-medium">{option.value}</span>
                                        {isSelected && <Check size={16} className="text-gold-400" />}
                                    </motion.button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Allergies */}
                    <div className="card-premium p-6">
                        <div className="flex items-center gap-3 mb-5">
                            <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
                                <AlertTriangle size={20} className="text-red-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-white">Allergies</h3>
                                <p className="text-sm text-slate-500">List any food allergies (comma separated)</p>
                            </div>
                        </div>
                        <input
                            type="text"
                            className="input-field-dark"
                            placeholder="e.g., Peanuts, Shellfish, Tree nuts"
                            value={profile.allergies.join(', ')}
                            onChange={(e) => setProfile({
                                ...profile,
                                allergies: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                            })}
                        />
                        {profile.allergies.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-3">
                                {profile.allergies.map((allergy, index) => (
                                    <span
                                        key={index}
                                        className="badge bg-red-500/20 text-red-400 border border-red-500/30"
                                    >
                                        {allergy}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Save Section */}
                    <div className="glass-frost rounded-xl p-6 flex flex-col sm:flex-row items-center justify-end gap-4">
                        <motion.button
                            type="submit"
                            disabled={saving}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="btn-primary flex items-center gap-2 px-8 w-full sm:w-auto justify-center"
                        >
                            {saving ? (
                                <>
                                    <Loader2 className="animate-spin" size={18} />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Save size={18} />
                                    Save Preferences
                                </>
                            )}
                        </motion.button>
                    </div>
                </motion.form>
            </div>
        </Layout>
    );
};

export default Profile;
