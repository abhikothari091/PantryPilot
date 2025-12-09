/**
 * Test setup for Vitest + React Testing Library
 */

import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Cleanup after each test
afterEach(() => {
    cleanup();
});

// Mock window.matchMedia (not available in happy-dom)
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => { },
        removeListener: () => { },
        addEventListener: () => { },
        removeEventListener: () => { },
        dispatchEvent: () => { },
    }),
});

// Mock localStorage - simplified version
const localStorageData: Record<string, string> = {};

const localStorageMock = {
    getItem: (key: string) => localStorageData[key] || null,
    setItem: (key: string, value: string) => {
        localStorageData[key] = value;
    },
    removeItem: (key: string) => {
        delete localStorageData[key];
    },
    clear: () => {
        Object.keys(localStorageData).forEach(key => delete localStorageData[key]);
    },
    get length() {
        return Object.keys(localStorageData).length;
    },
    key: (index: number) => {
        const keys = Object.keys(localStorageData);
        return keys[index] || null;
    },
};

Object.defineProperty(globalThis, 'localStorage', {
    value: localStorageMock,
    writable: true,
});
