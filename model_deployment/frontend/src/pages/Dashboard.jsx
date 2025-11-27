import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Plus, Trash2, Upload, Loader2, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Dashboard = () => {
    const [inventory, setInventory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [detectedItems, setDetectedItems] = useState([]);
    const [newItem, setNewItem] = useState({ item_name: '', quantity: '', unit: 'pcs', category: 'pantry' });
    const [uploading, setUploading] = useState(false);

    const fetchInventory = async () => {
        try {
            const res = await api.get('/inventory/');
            setInventory(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInventory();
    }, []);

    const handleAddItem = async (e) => {
        e.preventDefault();
        try {
            await api.post('/inventory/', {
                ...newItem,
                quantity: parseFloat(newItem.quantity)
            });
            setShowAddModal(false);
            setNewItem({ item_name: '', quantity: '', unit: 'pcs', category: 'pantry' });
            fetchInventory();
        } catch (err) {
            console.error(err);
        }
    };

    const handleDelete = async (id) => {
        try {
            await api.delete(`/inventory/${id}`);
            setInventory(inventory.filter(item => item.id !== id));
        } catch (err) {
            console.error(err);
        }
    };

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        setUploading(true);
        try {
            const res = await api.post('/inventory/upload', formData);
            if (res.data.status === 'success') {
                const detected = res.data.detected_items;
                // Show confirmation modal instead of auto-confirming
                setDetectedItems(detected);
                setShowConfirmModal(true);
            } else {
                alert('OCR failed: ' + (res.data.message || 'Unknown error'));
            }
        } catch (err) {
            console.error('Upload failed', err);
            alert('Upload failed: ' + (err.response?.data?.message || err.message));
        } finally {
            setUploading(false);
        }
    };

    const handleConfirmItems = async () => {
        try {
            await api.post('/inventory/confirm_upload', detectedItems);
            setShowConfirmModal(false);
            setDetectedItems([]);
            fetchInventory();
        } catch (err) {
            console.error('Failed to confirm items', err);
            alert('Failed to add items to inventory');
        }
    };

    const handleEditDetectedItem = (index, field, value) => {
        const updated = [...detectedItems];
        updated[index][field] = field === 'quantity' ? parseFloat(value) || 0 : value;
        setDetectedItems(updated);
    };

    const handleRemoveDetectedItem = (index) => {
        setDetectedItems(detectedItems.filter((_, i) => i !== index));
    };


    return (
        <Layout>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900">My Pantry</h1>
                    <p className="text-slate-500 mt-1">Manage your ingredients and stock</p>
                </div>
                <div className="flex gap-3">
                    <label className="btn-secondary flex items-center gap-2 cursor-pointer">
                        {uploading ? <Loader2 className="animate-spin" size={20} /> : <Upload size={20} />}
                        Scan Receipt
                        <input type="file" className="hidden" accept="image/*" onChange={handleFileUpload} disabled={uploading} />
                    </label>
                    <button onClick={() => setShowAddModal(true)} className="btn-primary flex items-center gap-2">
                        <Plus size={20} />
                        Add Item
                    </button>
                </div>
            </div>

            {/* OCR Scanning Loading Overlay */}
            <AnimatePresence>
                {uploading && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
                    >
                        <motion.div
                            initial={{ scale: 0.9 }}
                            animate={{ scale: 1 }}
                            className="bg-white rounded-2xl p-12 shadow-2xl"
                        >
                            <div className="flex flex-col items-center">
                                <motion.div
                                    animate={{ scale: [1, 1.1, 1] }}
                                    transition={{ duration: 1.5, repeat: Infinity }}
                                    className="text-7xl mb-6"
                                >
                                    🧾
                                </motion.div>
                                <motion.p
                                    animate={{ opacity: [1, 0.5, 1] }}
                                    transition={{ duration: 1.5, repeat: Infinity }}
                                    className="text-2xl font-bold bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent"
                                >
                                    Scanning your receipt...
                                </motion.p>
                                <p className="mt-2 text-slate-500">Extracting items with AI</p>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Inventory Grid */}
            {loading ? (
                <div className="flex justify-center py-12"><Loader2 className="animate-spin text-primary-500" size={32} /></div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <AnimatePresence>
                        {inventory.map((item) => (
                            <motion.div
                                key={item.id}
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex justify-between items-start"
                            >
                                <div>
                                    <h3 className="font-semibold text-slate-900">{item.item_name}</h3>
                                    <p className="text-sm text-slate-500 capitalize">{item.category}</p>
                                    <div className="mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-50 text-primary-700">
                                        {item.quantity} {item.unit}
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleDelete(item.id)}
                                    className="text-slate-400 hover:text-red-500 p-1 rounded-lg hover:bg-red-50 transition-colors"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}

            {/* OCR Confirmation Modal */}
            <AnimatePresence>
                {showConfirmModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
                        onClick={() => setShowConfirmModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden"
                        >
                            <div className="bg-gradient-to-r from-primary-600 to-accent-600 p-6 text-white">
                                <h2 className="text-2xl font-bold">Review Scanned Items</h2>
                                <p className="text-primary-100 mt-1">Please verify the items detected from your receipt</p>
                            </div>

                            <div className="p-6 overflow-y-auto max-h-[50vh]">
                                {detectedItems.length === 0 ? (
                                    <div className="text-center py-8 text-slate-500">
                                        <p>No items detected. Please try again with a clearer image.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {detectedItems.map((item, index) => (
                                            <div key={index} className="card p-4 flex items-center gap-4">
                                                <div className="flex-1 grid grid-cols-4 gap-3">
                                                    <div className="col-span-2">
                                                        <label className="text-xs font-medium text-slate-600 mb-1 block">Item Name</label>
                                                        <input
                                                            type="text"
                                                            value={item.item_name}
                                                            onChange={(e) => handleEditDetectedItem(index, 'item_name', e.target.value)}
                                                            className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-100 outline-none"
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="text-xs font-medium text-slate-600 mb-1 block">Quantity</label>
                                                        <input
                                                            type="number"
                                                            step="0.1"
                                                            value={item.quantity}
                                                            onChange={(e) => handleEditDetectedItem(index, 'quantity', e.target.value)}
                                                            className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-100 outline-none"
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="text-xs font-medium text-slate-600 mb-1 block">Unit</label>
                                                        <select
                                                            value={item.unit}
                                                            onChange={(e) => handleEditDetectedItem(index, 'unit', e.target.value)}
                                                            className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-100 outline-none"
                                                        >
                                                            <option value="pcs">pcs</option>
                                                            <option value="kg">kg</option>
                                                            <option value="g">g</option>
                                                            <option value="lb">lb</option>
                                                            <option value="oz">oz</option>
                                                            <option value="L">L</option>
                                                            <option value="ml">ml</option>
                                                        </select>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => handleRemoveDetectedItem(index)}
                                                    className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                                    title="Remove item"
                                                >
                                                    <Trash2 size={20} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="border-t border-slate-200 p-6 flex justify-between items-center bg-slate-50">
                                <button
                                    onClick={() => {
                                        setShowConfirmModal(false);
                                        setDetectedItems([]);
                                    }}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleConfirmItems}
                                    disabled={detectedItems.length === 0}
                                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Add {detectedItems.length} Item{detectedItems.length !== 1 ? 's' : ''} to Inventory
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Add Item Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl"
                    >
                        <h2 className="text-xl font-bold mb-4">Add New Item</h2>
                        <form onSubmit={handleAddItem} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Item Name</label>
                                <input
                                    type="text"
                                    required
                                    className="input-field"
                                    value={newItem.item_name}
                                    onChange={e => setNewItem({ ...newItem, item_name: e.target.value })}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">Quantity</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        required
                                        className="input-field"
                                        value={newItem.quantity}
                                        onChange={e => setNewItem({ ...newItem, quantity: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">Unit</label>
                                    <select
                                        className="input-field"
                                        value={newItem.unit}
                                        onChange={e => setNewItem({ ...newItem, unit: e.target.value })}
                                    >
                                        <option value="pcs">pcs</option>
                                        <option value="kg">kg</option>
                                        <option value="g">g</option>
                                        <option value="oz">oz</option>
                                        <option value="lb">lb</option>
                                        <option value="L">L</option>
                                        <option value="ml">ml</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                                <select
                                    className="input-field"
                                    value={newItem.category}
                                    onChange={e => setNewItem({ ...newItem, category: e.target.value })}
                                >
                                    <option value="pantry">Pantry</option>
                                    <option value="produce">Produce</option>
                                    <option value="dairy">Dairy</option>
                                    <option value="meat">Meat</option>
                                    <option value="frozen">Frozen</option>
                                    <option value="beverages">Beverages</option>
                                </select>
                            </div>
                            <div className="flex justify-end gap-3 mt-6">
                                <button type="button" onClick={() => setShowAddModal(false)} className="btn-secondary">Cancel</button>
                                <button type="submit" className="btn-primary">Add Item</button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </Layout>
    );
};

export default Dashboard;
