import React from 'react';

/**
 * Subtle, performant snowfall animation component.
 * Uses CSS-only animations for optimal performance.
 * Can be toggled via the `enabled` prop for accessibility.
 */
const Snowfall = ({ enabled = true, density = 'normal' }) => {
    if (!enabled) return null;

    const snowflakeCount = density === 'light' ? 6 : density === 'heavy' ? 15 : 10;

    return (
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
            {[...Array(snowflakeCount)].map((_, i) => (
                <span key={i} className="snowflake">❄</span>
            ))}
        </div>
    );
};

export default Snowfall;
