import React from 'react';
import { motion } from 'framer-motion';

// Subtle page transition wrapper
const PageTransition = ({ children }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{
                duration: 0.2,
                ease: 'easeOut'
            }}
        >
            {children}
        </motion.div>
    );
};

export default PageTransition;
