import React, { useState, useEffect } from 'react';
import { Steps } from 'intro.js-react';
import { useLocation, useNavigate } from 'react-router-dom';
import 'intro.js/introjs.css';
import './AppTour.css';

const AppTour = ({ enabled, onExit }) => {
    const navigate = useNavigate();
    const location = useLocation();

    // Controlled step index to manage flow manually
    const [currentStep, setCurrentStep] = useState(0);

    // We define steps in a way that respects the current route, but for a guided tour
    // we want to force a specific path: Dashboard -> Recipes -> Profile.
    // The 'element' selectors must exist on the page for intro.js to find them.
    // If we are navigating, we might need to delay step transitions? 
    // Actually, intro.js works best if all elements are present, OR we handle navigation manually.
    // For a multi-page tour, standard intro.js often requires splitting tours or careful handling.
    // However, we can use the `onBeforeChange` callback to navigate.

    const tourSteps = [
        {
            element: 'body',
            intro: 'Welcome to **PantryPilot**! 🍳<br><br>Let\'s take a quick tour to show you how to manage your pantry and generate delicious recipes.',
            position: 'center',
            route: '/dashboard'
        },
        // --- Dashboard Steps ---
        {
            element: '#nav-dashboard',
            intro: 'This is your **Inventory Dashboard**. It keeps track of all your ingredients.',
            route: '/dashboard'
        },
        {
            element: '#btn-scan-receipt',
            intro: 'Got a receipt? Click here to **Scan** it! 📸<br>We\'ll automatically detect items and add them to your pantry.',
            route: '/dashboard'
        },
        {
            element: '#btn-add-item',
            intro: 'Or manually **Add Items** one by one using this button.',
            route: '/dashboard'
        },
        // --- Recipe Steps ---
        {
            element: '#nav-recipes',
            intro: 'Hungry? Head over to the **Recipes** tab.',
            route: '/recipes'
        },
        {
            element: '#input-recipe-query',
            intro: 'Tell us what you want to eat! 🍝<br>e.g., "Spicy pasta" or "High protein breakfast".',
            route: '/recipes'
        },
        {
            element: '#btn-generate-recipe',
            intro: 'Click **Generate** and we will create a custom recipe using ingredients you already have!',
            route: '/recipes'
        },
        // --- Profile Steps ---
        {
            element: '#nav-profile',
            intro: 'Make sure to set up your **Profile**.',
            route: '/profile'
        },
        {
            element: '#section-dietary',
            intro: 'Here you can set **Dietary Restrictions** (like Vegan or Gluten-Free) so we only suggest safe recipes.',
            route: '/profile'
        },
        // --- Finish ---
        {
            element: '#user-section',
            intro: 'That\'s it! You\'re ready to cook. 👨‍🍳<br>Manage your account settings here.',
            route: '/profile'
        }
    ];

    // Reset step when tour is enabled
    useEffect(() => {
        if (enabled) {
            // Only reset if we are starting fresh (could add more logic if needed)
            // But relying on parent 'enabled' toggle is usually enough.
            // check if we are just starting? 
            // Better: only reset if we are not already in a specific step? 
            // Actually, simply removing location.pathname fixes the reset-on-nav bug.
            setCurrentStep(0);
            if (location.pathname !== '/dashboard') {
                navigate('/dashboard');
            }
        }
    }, [enabled, navigate]);

    const handleChange = (nextStepIndex) => {
        const nextStep = tourSteps[nextStepIndex];

        // If we are moving to a step that requires a different route
        if (nextStep && nextStep.route && location.pathname !== nextStep.route) {
            // Update state so the new instance starts at the right step
            setCurrentStep(nextStepIndex);
            // Navigate to trigger re-render and Steps remount via key prop
            navigate(nextStep.route);
        } else {
            setCurrentStep(nextStepIndex);
        }
    };

    return (
        <Steps
            key={location.pathname} // Force remount on route change to handle multi-page tour correctly
            enabled={enabled}
            steps={tourSteps}
            initialStep={currentStep}
            onExit={onExit}
            onChange={handleChange}
            options={{
                showProgress: true,
                showBullets: true,
                exitOnOverlayClick: true,
                disableInteraction: true,
                keyboardNavigation: true,
                doneLabel: 'Let\'s Cook!',
                nextLabel: 'Next',
                prevLabel: 'Back',
                scrollToElement: true,
                overlayOpacity: 0.8,
            }}
        />
    );
};

export default AppTour;
