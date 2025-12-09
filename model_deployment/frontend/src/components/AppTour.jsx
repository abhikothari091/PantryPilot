import React, { useState, useEffect } from 'react';
import Joyride, { STATUS, ACTIONS } from 'react-joyride';
import './AppTour.css';

const AppTour = ({ enabled, onExit }) => {
    const [run, setRun] = useState(false);

    // Simple tour of sidebar navigation - works from any page!
    const steps = [
        {
            target: 'body',
            content: (
                <div className="tour-content">
                    <h3>Welcome to PantryPilot! 🍳</h3>
                    <p>Your AI-powered kitchen assistant. Let's show you around!</p>
                </div>
            ),
            placement: 'center',
            disableBeacon: true,
        },
        {
            target: '#nav-dashboard',
            content: (
                <div className="tour-content">
                    <h3>📦 Inventory Dashboard</h3>
                    <p>This is your pantry headquarters! View all your ingredients, track quantities, and get low-stock alerts.</p>
                </div>
            ),
            disableBeacon: true,
        },
        {
            target: '#nav-recipes',
            content: (
                <div className="tour-content">
                    <h3>👨‍🍳 Recipe Generator</h3>
                    <p>Tell us what you're craving! Our AI creates <strong>personalized recipes</strong> using ingredients you already have.</p>
                </div>
            ),
            disableBeacon: true,
        },
        {
            target: '#nav-history',
            content: (
                <div className="tour-content">
                    <h3>📜 Recipe History</h3>
                    <p>All your generated recipes are saved here. Revisit your favorites anytime!</p>
                </div>
            ),
            disableBeacon: true,
        },
        {
            target: '#nav-profile',
            content: (
                <div className="tour-content">
                    <h3>⚙️ Your Profile</h3>
                    <p>Set your <strong>dietary restrictions</strong>, allergies, and cuisine preferences. We'll tailor all recipes just for you!</p>
                </div>
            ),
            disableBeacon: true,
        },
        {
            target: '#user-section',
            content: (
                <div className="tour-content">
                    <h3>You're All Set! 🎉</h3>
                    <p>Start by adding some ingredients to your inventory, then head to Recipes to cook something delicious!</p>
                </div>
            ),
            disableBeacon: true,
        },
    ];

    // Start tour when enabled
    useEffect(() => {
        setRun(enabled);
    }, [enabled]);

    const handleJoyrideCallback = (data) => {
        const { status, action } = data;

        // Handle finish, skip, or close (X button)
        if ([STATUS.FINISHED, STATUS.SKIPPED].includes(status) || action === ACTIONS.CLOSE) {
            setRun(false);
            onExit();
        }
    };

    // Custom styles matching the app's dark glassmorphism theme
    const joyrideStyles = {
        options: {
            arrowColor: 'rgba(30, 41, 59, 0.98)',
            backgroundColor: 'rgba(30, 41, 59, 0.98)',
            overlayColor: 'rgba(0, 0, 0, 0.8)',
            primaryColor: '#06b6d4',
            textColor: '#e2e8f0',
            zIndex: 10000,
        },
        tooltip: {
            borderRadius: 16,
            padding: 0,
            overflow: 'hidden',
        },
        tooltipContainer: {
            textAlign: 'left',
            padding: '20px 24px',
        },
        buttonNext: {
            backgroundColor: '#06b6d4',
            borderRadius: 10,
            color: '#0f172a',
            fontWeight: 600,
            fontSize: '0.9rem',
            padding: '10px 24px',
        },
        buttonBack: {
            color: '#94a3b8',
            marginRight: 10,
            fontSize: '0.9rem',
        },
        buttonSkip: {
            color: '#64748b',
            fontSize: '0.85rem',
        },
        spotlight: {
            borderRadius: 12,
        },
    };

    return (
        <Joyride
            steps={steps}
            run={run}
            continuous
            showSkipButton
            showProgress
            callback={handleJoyrideCallback}
            styles={joyrideStyles}
            locale={{
                back: 'Back',
                close: 'Close',
                last: "Let's Cook! 🍳",
                next: 'Next',
                skip: 'Skip',
            }}
        />
    );
};

export default AppTour;
