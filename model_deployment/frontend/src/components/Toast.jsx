import React, { createContext, useContext, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertCircle, Info, X, AlertTriangle } from 'lucide-react';

const ToastContext = createContext();

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};

const Toast = ({ toast, onDismiss }) => {
    const icons = {
        success: <CheckCircle className="text-evergreen-400" size={20} />,
        error: <AlertCircle className="text-red-400" size={20} />,
        warning: <AlertTriangle className="text-gold-400" size={20} />,
        info: <Info className="text-frost-400" size={20} />,
    };

    const backgrounds = {
        success: 'bg-evergreen-500/10 border-evergreen-500/30',
        error: 'bg-red-500/10 border-red-500/30',
        warning: 'bg-gold-500/10 border-gold-500/30',
        info: 'bg-frost-500/10 border-frost-500/30',
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-lg max-w-sm ${backgrounds[toast.type]}`}
        >
            {icons[toast.type]}
            <p className="text-white text-sm flex-1">{toast.message}</p>
            <button
                onClick={() => onDismiss(toast.id)}
                className="text-slate-400 hover:text-white transition-colors p-1"
            >
                <X size={16} />
            </button>
        </motion.div>
    );
};

export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info', duration = 4000) => {
        const id = Date.now() + Math.random();
        setToasts((prev) => [...prev, { id, message, type }]);

        if (duration > 0) {
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id));
            }, duration);
        }

        return id;
    }, []);

    const dismissToast = useCallback((id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const toast = {
        success: (message, duration) => addToast(message, 'success', duration),
        error: (message, duration) => addToast(message, 'error', duration),
        warning: (message, duration) => addToast(message, 'warning', duration),
        info: (message, duration) => addToast(message, 'info', duration),
    };

    return (
        <ToastContext.Provider value={toast}>
            {children}

            {/* Toast Container */}
            <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
                <AnimatePresence>
                    {toasts.map((t) => (
                        <Toast key={t.id} toast={t} onDismiss={dismissToast} />
                    ))}
                </AnimatePresence>
            </div>
        </ToastContext.Provider>
    );
};

export default ToastProvider;
