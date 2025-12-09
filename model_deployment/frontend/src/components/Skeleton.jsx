import React from 'react';

// Base skeleton with shimmer effect
export const Skeleton = ({ className = '', children }) => (
    <div className={`animate-pulse bg-secondary-800/50 rounded-lg ${className}`}>
        {children}
    </div>
);

// Text line skeleton
export const SkeletonText = ({ lines = 1, className = '' }) => (
    <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
            <div
                key={i}
                className={`h-4 bg-secondary-700/50 rounded ${i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'}`}
            />
        ))}
    </div>
);

// Circle skeleton (for avatars)
export const SkeletonCircle = ({ size = 40, className = '' }) => (
    <div
        className={`rounded-full bg-secondary-700/50 ${className}`}
        style={{ width: size, height: size }}
    />
);

// Card skeleton for inventory items
export const SkeletonCard = ({ className = '' }) => (
    <div className={`card p-4 animate-pulse ${className}`}>
        <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-secondary-700/50" />
            <div className="flex-1 space-y-2">
                <div className="h-5 bg-secondary-700/50 rounded w-3/4" />
                <div className="h-4 bg-secondary-700/50 rounded w-1/2" />
            </div>
        </div>
    </div>
);

// Recipe card skeleton
export const SkeletonRecipeCard = ({ className = '' }) => (
    <div className={`card-premium p-5 animate-pulse ${className}`}>
        <div className="flex items-start justify-between mb-3">
            <div className="flex-1 space-y-2">
                <div className="h-6 bg-secondary-700/50 rounded w-3/4" />
                <div className="h-4 bg-secondary-700/50 rounded w-1/2" />
            </div>
            <div className="w-10 h-10 rounded-lg bg-secondary-700/50" />
        </div>
        <div className="flex gap-2 mt-4">
            <div className="h-6 bg-secondary-700/50 rounded-full w-20" />
            <div className="h-6 bg-secondary-700/50 rounded-full w-16" />
        </div>
    </div>
);

// Inventory grid skeleton
export const SkeletonInventoryGrid = ({ count = 6 }) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: count }).map((_, i) => (
            <SkeletonCard key={i} />
        ))}
    </div>
);

// Recipe history skeleton
export const SkeletonHistoryGrid = ({ count = 6 }) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: count }).map((_, i) => (
            <SkeletonRecipeCard key={i} />
        ))}
    </div>
);

// Profile form skeleton
export const SkeletonProfileForm = () => (
    <div className="space-y-8 animate-pulse">
        {[1, 2, 3].map((section) => (
            <div key={section} className="card-premium p-6">
                <div className="flex items-center gap-3 mb-5">
                    <div className="w-10 h-10 rounded-xl bg-secondary-700/50" />
                    <div className="space-y-2">
                        <div className="h-5 bg-secondary-700/50 rounded w-40" />
                        <div className="h-3 bg-secondary-700/50 rounded w-56" />
                    </div>
                </div>
                <div className="flex flex-wrap gap-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="h-10 bg-secondary-700/50 rounded-xl w-24" />
                    ))}
                </div>
            </div>
        ))}
    </div>
);

// Full page loading skeleton
export const SkeletonPage = ({ title = true }) => (
    <div className="animate-pulse">
        {title && (
            <div className="mb-8">
                <div className="h-10 bg-secondary-700/50 rounded w-64 mb-2" />
                <div className="h-4 bg-secondary-700/50 rounded w-48" />
            </div>
        )}
        <SkeletonInventoryGrid count={6} />
    </div>
);

export default {
    Skeleton,
    SkeletonText,
    SkeletonCircle,
    SkeletonCard,
    SkeletonRecipeCard,
    SkeletonInventoryGrid,
    SkeletonHistoryGrid,
    SkeletonProfileForm,
    SkeletonPage
};
