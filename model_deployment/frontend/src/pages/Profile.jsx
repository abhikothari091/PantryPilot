import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Save, Loader2 } from 'lucide-react';

const Profile = () => {
    const [profile, setProfile] = useState({
        dietary_restrictions: [],
        allergies: [],
        favorite_cuisines: []
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

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
        setMessage('');
        try {
            await api.put('/users/profile', profile);
            setMessage('Profile updated successfully!');
            setTimeout(() => setMessage(''), 3000);
        } catch (err) {
            console.error(err);
            setMessage('Failed to update profile.');
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

    const DIETARY_OPTIONS = ['Vegan', 'Vegetarian', 'Gluten-Free', 'Dairy-Free', 'Keto', 'Paleo'];
    const CUISINE_OPTIONS = ['Italian', 'Chinese', 'Mexican', 'Indian', 'Japanese', 'Thai', 'Mediterranean', 'American'];

    if (loading) return <Layout><div className="flex justify-center py-12"><Loader2 className="animate-spin" /></div></Layout>;

    return (
        <Layout>
            <div className="max-w-2xl mx-auto">
                <h1 className="text-3xl font-bold text-slate-900 mb-2">My Preferences</h1>
                <p className="text-slate-500 mb-8">Customize your dietary needs for better recommendations.</p>

                <form onSubmit={handleSave} className="space-y-8 bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">

                    {/* Dietary Restrictions */}
                    <div>
                        <h3 className="text-lg font-semibold text-slate-900 mb-4">Dietary Restrictions</h3>
                        <div className="flex flex-wrap gap-3">
                            {DIETARY_OPTIONS.map(option => (
                                <button
                                    key={option}
                                    type="button"
                                    onClick={() => toggleItem('dietary_restrictions', option)}
                                    className={`px-4 py-2 rounded-lg border transition-all ${profile.dietary_restrictions.includes(option)
                                            ? 'bg-primary-50 border-primary-500 text-primary-700 font-medium'
                                            : 'border-slate-200 text-slate-600 hover:border-slate-300'
                                        }`}
                                >
                                    {option}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Cuisines */}
                    <div>
                        <h3 className="text-lg font-semibold text-slate-900 mb-4">Favorite Cuisines</h3>
                        <div className="flex flex-wrap gap-3">
                            {CUISINE_OPTIONS.map(option => (
                                <button
                                    key={option}
                                    type="button"
                                    onClick={() => toggleItem('favorite_cuisines', option)}
                                    className={`px-4 py-2 rounded-lg border transition-all ${profile.favorite_cuisines.includes(option)
                                            ? 'bg-purple-50 border-purple-500 text-purple-700 font-medium'
                                            : 'border-slate-200 text-slate-600 hover:border-slate-300'
                                        }`}
                                >
                                    {option}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Allergies (Simple Text Input for now, could be tags) */}
                    <div>
                        <h3 className="text-lg font-semibold text-slate-900 mb-4">Allergies</h3>
                        <input
                            type="text"
                            className="input-field"
                            placeholder="e.g., Peanuts, Shellfish (comma separated)"
                            value={profile.allergies.join(', ')}
                            onChange={(e) => setProfile({ ...profile, allergies: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                        />
                    </div>

                    <div className="pt-6 border-t border-slate-100 flex items-center justify-between">
                        <span className={`text-sm ${message.includes('success') ? 'text-green-600' : 'text-red-600'}`}>
                            {message}
                        </span>
                        <button
                            type="submit"
                            disabled={saving}
                            className="btn-primary flex items-center gap-2 px-8"
                        >
                            {saving ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
                            Save Changes
                        </button>
                    </div>
                </form>
            </div>
        </Layout>
    );
};

export default Profile;
