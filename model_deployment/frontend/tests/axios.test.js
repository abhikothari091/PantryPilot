/**
 * Tests for axios API client - interceptors, base URL, error handling
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Don't mock axios - test the actual api instance
describe('Axios API Client', () => {
    beforeEach(() => {
        localStorage.clear();
        // Clear any previous mocks
        vi.clearAllMocks();
    });

    it('should have correct base URL configuration', async () => {
        // Dynamically import to get fresh instance
        const { default: api } = await import('../src/api/axios');

        expect(api.defaults.baseURL).toBeDefined();
        expect(typeof api.defaults.baseURL).toBe('string');
    });

    it('should have request interceptor configured', async () => {
        const { default: api } = await import('../src/api/axios');

        // Check that interceptors exist
        expect(api.interceptors.request).toBeDefined();
        expect(api.interceptors.request.handlers.length).toBeGreaterThan(0);
    });

    it('should attach JWT token from localStorage to requests', async () => {
        const { default: api } = await import('../src/api/axios');

        // Set token in localStorage
        localStorage.setItem('token', 'test_jwt_token');

        // Get the interceptor handler
        const interceptor = api.interceptors.request.handlers[0];

        // Simulate request config
        const config = { headers: {} };
        const result = await interceptor.fulfilled(config);

        expect(result.headers.Authorization).toBe('Bearer test_jwt_token');
    });

    it('should not attach token when not in localStorage', async () => {
        const { default: api } = await import('../src/api/axios');

        // Ensure no token in localStorage
        localStorage.removeItem('token');

        const interceptor = api.interceptors.request.handlers[0];
        const config = { headers: {} };
        const result = await interceptor.fulfilled(config);

        expect(result.headers.Authorization).toBeUndefined();
    });
});
