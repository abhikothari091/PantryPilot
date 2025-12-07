import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Plus, Trash2, Upload, Loader2, Edit2, Package, AlertTriangle, Check, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '../components/Toast';
import { SkeletonInventoryGrid } from '../components/Skeleton';

const Dashboard = () => {
    const toast = useToast();
    const [inventory, setInventory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [detectedItems, setDetectedItems] = useState([]);
    const [newItem, setNewItem] = useState({ item_name: '', quantity: '', unit: 'pcs', category: 'pantry' });
    const [uploading, setUploading] = useState(false);
    const [editingItem, setEditingItem] = useState(null);
    const [confirmEdit, setConfirmEdit] = useState(false);
    const [pendingEdit, setPendingEdit] = useState(null);
    const [pendingDelete, setPendingDelete] = useState(null);

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

    const handleUpdateItem = async () => {
        if (!pendingEdit) return;
        try {
            await api.put(`/inventory/${pendingEdit.id}`, {
                item_name: pendingEdit.item_name,
                quantity: parseFloat(pendingEdit.quantity),
                unit: pendingEdit.unit,
                category: pendingEdit.category,
            });
            setEditingItem(null);
            setPendingEdit(null);
            setConfirmEdit(false);
            fetchInventory();
            toast.success('Item updated!');
        } catch (err) {
            console.error(err);
            toast.error('Failed to update item');
        } finally {
            setConfirmEdit(false);
            setPendingEdit(null);
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
            toast.success(`${newItem.item_name} added to inventory!`);
        } catch (err) {
            console.error(err);
            toast.error('Failed to add item');
        }
    };

    const handleDelete = async () => {
        if (!pendingDelete) return;
        try {
            await api.delete(`/inventory/${pendingDelete}`);
            setInventory(inventory.filter(item => item.id !== pendingDelete));
            toast.success('Item removed');
        } catch (err) {
            console.error(err);
            toast.error('Failed to delete item');
        } finally {
            setPendingDelete(null);
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
                setDetectedItems(detected);
                setShowConfirmModal(true);
            } else {
                toast.error('OCR failed: ' + (res.data.message || 'Unknown error'));
            }
        } catch (err) {
            console.error('Upload failed', err);
            toast.error('Upload failed: ' + (err.response?.data?.message || err.message));
        } finally {
            setUploading(false);
        }
    };

    const handleConfirmItems = async () => {
        try {
            await api.post('/inventory/confirm_upload', detectedItems);
            setShowConfirmModal(false);
            toast.success(`${detectedItems.length} items added to inventory!`);
            setDetectedItems([]);
            fetchInventory();
        } catch (err) {
            console.error('Failed to confirm items', err);
            toast.error('Failed to add items to inventory');
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

    const getCategoryIcon = (category) => {
        const icons = {
            pantry: '🥫',
            produce: '🥬',
            dairy: '🧀',
            meat: '🥩',
            frozen: '🧊',
            beverages: '🥤',
        };
        return icons[category] || '📦';
    };

    return (
        <Layout>
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                <div>
                    <h1 className="text-3xl md:text-4xl font-bold font-display text-gradient mb-1">
                        My Pantry
                    </h1>
                    <p className="text-slate-400">Manage your ingredients and stock</p>
                </div>
                <div className="flex gap-3 w-full md:w-auto">
                    <label className="btn-secondary flex items-center gap-2 cursor-pointer flex-1 md:flex-none justify-center">
                        {uploading ? <Loader2 className="animate-spin" size={18} /> : <Upload size={18} />}
                        <span className="hidden sm:inline">Scan Receipt</span>
                        <span className="sm:hidden">Scan</span>
                        <input type="file" className="hidden" accept="image/*" onChange={handleFileUpload} disabled={uploading} />
                    </label>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="btn-primary flex items-center gap-2 flex-1 md:flex-none justify-center"
                    >
                        <Plus size={18} />
                        <span className="hidden sm:inline">Add Item</span>
                        <span className="sm:hidden">Add</span>
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
                        className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
                    >
                        <motion.div
                            initial={{ scale: 0.9 }}
                            animate={{ scale: 1 }}
                            className="glass-panel-solid rounded-3xl p-12 shadow-2xl text-center"
                        >
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
                                className="text-2xl font-bold text-gradient mb-2"
                            >
                                Scanning your receipt...
                            </motion.p>
                            <p className="text-slate-400">Extracting items with AI</p>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Inventory Grid */}
            {loading ? (
                <SkeletonInventoryGrid count={6} />
            ) : inventory.length === 0 ? (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center py-20"
                >
                    <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-secondary-800/50 flex items-center justify-center">
                        <Package size={48} className="text-slate-600" />
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">Your pantry is empty</h3>
                    <p className="text-slate-400 mb-6">Start by adding items or scanning a receipt</p>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="btn-primary"
                    >
                        <Plus size={18} className="inline mr-2" />
                        Add Your First Item
                    </button>
                </motion.div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    <AnimatePresence>
                        {inventory.map((item, index) => (
                            <motion.div
                                key={item.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ delay: index * 0.03 }}
                                className="card p-5 group"
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <span className="text-2xl">{getCategoryIcon(item.category)}</span>
                                        <div>
                                            <h3 className="font-semibold text-white group-hover:text-primary-400 transition-colors">
                                                {item.item_name}
                                            </h3>
                                            <p className="text-sm text-slate-500 capitalize">{item.category}</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="badge-frost">
                                            {item.quantity} {item.unit}
                                        </span>
                                        {Number(item.quantity) <= 0.1 && (
                                            <span className="badge bg-red-500/20 text-red-400 border border-red-500/30 flex items-center gap-1">
                                                <AlertTriangle size={12} />
                                                Low
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => setEditingItem({ ...item })}
                                            className="p-2 text-slate-400 hover:text-frost-400 hover:bg-frost-500/10 rounded-lg transition-all"
                                        >
                                            <Edit2 size={16} />
                                        </button>
                                        <button
                                            onClick={() => setPendingDelete(item.id)}
                                            className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
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
                        className="modal-overlay"
                        onClick={() => setShowConfirmModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="glass-panel-solid rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden border border-white/10"
                        >
                            <div className="bg-gradient-to-r from-primary-600 to-gold-500 p-6 text-white">
                                <h2 className="text-2xl font-bold font-display">Review Scanned Items</h2>
                                <p className="text-white/80 mt-1">Verify the items detected from your receipt</p>
                            </div>

                            <div className="p-6 overflow-y-auto max-h-[50vh]">
                                {detectedItems.length === 0 ? (
                                    <div className="text-center py-8 text-slate-400">
                                        <p>No items detected. Please try again with a clearer image.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {detectedItems.map((item, index) => (
                                            <div key={index} className="card p-4 flex items-center gap-4">
                                                <div className="flex-1 grid grid-cols-4 gap-3">
                                                    <div className="col-span-2">
                                                        <label className="text-xs font-medium text-slate-400 mb-1 block">Item Name</label>
                                                        <input
                                                            type="text"
                                                            value={item.item_name}
                                                            onChange={(e) => handleEditDetectedItem(index, 'item_name', e.target.value)}
                                                            className="input-field-dark text-sm py-2"
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="text-xs font-medium text-slate-400 mb-1 block">Quantity</label>
                                                        <input
                                                            type="number"
                                                            step="0.1"
                                                            value={item.quantity}
                                                            onChange={(e) => handleEditDetectedItem(index, 'quantity', e.target.value)}
                                                            className="input-field-dark text-sm py-2"
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="text-xs font-medium text-slate-400 mb-1 block">Unit</label>
                                                        <select
                                                            value={item.unit}
                                                            onChange={(e) => handleEditDetectedItem(index, 'unit', e.target.value)}
                                                            className="input-field-dark text-sm py-2"
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
                                                    className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                                    title="Remove item"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="border-t border-white/5 p-6 flex justify-between items-center bg-secondary-900/50">
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
            <AnimatePresence>
                {showAddModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="modal-overlay"
                        onClick={() => setShowAddModal(false)}
                    >
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            onClick={(e) => e.stopPropagation()}
                            className="modal-content"
                        >
                            <div className="modal-header">
                                <h2 className="text-xl font-bold text-white">Add New Item</h2>
                                <p className="text-slate-400 text-sm mt-1">Add an ingredient to your pantry</p>
                            </div>
                            <form onSubmit={handleAddItem}>
                                <div className="modal-body space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-300 mb-2">Item Name</label>
                                        <input
                                            type="text"
                                            required
                                            className="input-field-dark"
                                            placeholder="e.g., Olive Oil"
                                            value={newItem.item_name}
                                            onChange={e => setNewItem({ ...newItem, item_name: e.target.value })}
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-slate-300 mb-2">Quantity</label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                required
                                                className="input-field-dark"
                                                placeholder="1"
                                                value={newItem.quantity}
                                                onChange={e => setNewItem({ ...newItem, quantity: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-slate-300 mb-2">Unit</label>
                                            <select
                                                className="input-field-dark"
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
                                        <label className="block text-sm font-medium text-slate-300 mb-2">Category</label>
                                        <select
                                            className="input-field-dark"
                                            value={newItem.category}
                                            onChange={e => setNewItem({ ...newItem, category: e.target.value })}
                                        >
                                            <option value="pantry">🥫 Pantry</option>
                                            <option value="produce">🥬 Produce</option>
                                            <option value="dairy">🧀 Dairy</option>
                                            <option value="meat">🥩 Meat</option>
                                            <option value="frozen">🧊 Frozen</option>
                                            <option value="beverages">🥤 Beverages</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button type="button" onClick={() => setShowAddModal(false)} className="btn-secondary">
                                        Cancel
                                    </button>
                                    <button type="submit" className="btn-primary">
                                        <Plus size={18} className="inline mr-1" />
                                        Add Item
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Edit Item Modal */}
            <AnimatePresence>
                {editingItem && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="modal-overlay"
                        onClick={() => setEditingItem(null)}
                    >
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            onClick={(e) => e.stopPropagation()}
                            className="modal-content"
                        >
                            <div className="modal-header">
                                <h2 className="text-xl font-bold text-white">Edit Item</h2>
                                <p className="text-slate-400 text-sm mt-1">Update item details</p>
                            </div>
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault();
                                    setPendingEdit(editingItem);
                                    setConfirmEdit(true);
                                }}
                            >
                                <div className="modal-body space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-300 mb-2">Item Name</label>
                                        <input
                                            type="text"
                                            required
                                            className="input-field-dark"
                                            value={editingItem.item_name}
                                            onChange={e => setEditingItem({ ...editingItem, item_name: e.target.value })}
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-slate-300 mb-2">Quantity</label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                required
                                                className="input-field-dark"
                                                value={editingItem.quantity}
                                                onChange={e => setEditingItem({ ...editingItem, quantity: e.target.value })}
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-slate-300 mb-2">Unit</label>
                                            <select
                                                className="input-field-dark"
                                                value={editingItem.unit}
                                                onChange={e => setEditingItem({ ...editingItem, unit: e.target.value })}
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
                                        <label className="block text-sm font-medium text-slate-300 mb-2">Category</label>
                                        <select
                                            className="input-field-dark"
                                            value={editingItem.category}
                                            onChange={e => setEditingItem({ ...editingItem, category: e.target.value })}
                                        >
                                            <option value="pantry">🥫 Pantry</option>
                                            <option value="produce">🥬 Produce</option>
                                            <option value="dairy">🧀 Dairy</option>
                                            <option value="meat">🥩 Meat</option>
                                            <option value="frozen">🧊 Frozen</option>
                                            <option value="beverages">🥤 Beverages</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button type="button" onClick={() => setEditingItem(null)} className="btn-secondary">
                                        Cancel
                                    </button>
                                    <button type="submit" className="btn-primary">
                                        <Check size={18} className="inline mr-1" />
                                        Save Changes
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Edit Confirmation Modal */}
            <AnimatePresence>
                {confirmEdit && pendingEdit && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="modal-overlay"
                        onClick={() => setConfirmEdit(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="modal-content max-w-md"
                        >
                            <div className="modal-body text-center py-8">
                                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gold-500/20 flex items-center justify-center">
                                    <Edit2 size={28} className="text-gold-400" />
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-2">Confirm Update</h3>
                                <p className="text-slate-400">
                                    Save changes to <strong className="text-white">{pendingEdit.item_name}</strong>?
                                </p>
                            </div>
                            <div className="modal-footer justify-center">
                                <button onClick={() => setConfirmEdit(false)} className="btn-secondary">
                                    Cancel
                                </button>
                                <button onClick={handleUpdateItem} className="btn-primary">
                                    Confirm
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Delete Confirmation Modal */}
            <AnimatePresence>
                {pendingDelete !== null && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="modal-overlay"
                        onClick={() => setPendingDelete(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="modal-content max-w-md"
                        >
                            <div className="modal-body text-center py-8">
                                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
                                    <Trash2 size={28} className="text-red-400" />
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-2">Delete Item</h3>
                                <p className="text-slate-400">
                                    Are you sure you want to delete this item from your inventory?
                                </p>
                            </div>
                            <div className="modal-footer justify-center">
                                <button onClick={() => setPendingDelete(null)} className="btn-secondary">
                                    Cancel
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white font-semibold py-2.5 px-5 rounded-xl shadow-lg transition-all"
                                >
                                    Delete
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </Layout>
    );
};

export default Dashboard;
