/**
 * Tests for AuthContext - login, logout, register, token management
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../src/context/AuthContext';
import api from '../src/api/axios';

// Mock axios
vi.mock('../src/api/axios');

describe('AuthContext', () => {
    beforeEach(() => {
        // Clear localStorage before each test
        localStorage.clear();
        vi.clearAllMocks();

        // Default mock: no stored token
        api.get.mockRejectedValue(new Error('No token'));
    });

    describe('useAuth hook', () => {
        it('should provide auth context', async () => {
            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            expect(result.current).toHaveProperty('user');
            expect(result.current).toHaveProperty('login');
            expect(result.current).toHaveProperty('logout');
            expect(result.current).toHaveProperty('register');
            expect(result.current).toHaveProperty('loading');

            // Wait for initial load to complete
            await waitFor(() => expect(result.current.loading).toBe(false));
        });

        it('should eventually set loading to false', async () => {
            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            // Wait for loading to become false
            await waitFor(() => expect(result.current.loading).toBe(false));
            expect(result.current.user).toBeNull();
        });
    });

    describe('login', () => {
        it('should login successfully with valid credentials', async () => {
            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            // Wait for initial load
            await waitFor(() => expect(result.current.loading).toBe(false));

            // Setup mocks for login sequence
            api.post.mockResolvedValueOnce({
                data: { access_token: 'test_token', token_type: 'bearer' },
            });
            api.get.mockResolvedValueOnce({
                data: {
                    username: 'testuser',
                    email: 'test@example.com',
                    dietary_restrictions: ['vegan'],
                },
            });
            // Mock warmup endpoint (fire-and-forget)
            api.post.mockResolvedValueOnce({ data: { status: 'warming' } });

            await act(async () => {
                await result.current.login('testuser', 'password123');
            });

            expect(result.current.user).toEqual({
                username: 'testuser',
                email: 'test@example.com',
                dietary_restrictions: ['vegan'],
            });
            expect(localStorage.getItem('token')).toBe('test_token');
        });

        it('should call warmup endpoint after successful login', async () => {
            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            await waitFor(() => expect(result.current.loading).toBe(false));

            // Setup login mocks
            api.post.mockResolvedValueOnce({
                data: { access_token: 'test_token', token_type: 'bearer' },
            });
            api.get.mockResolvedValueOnce({
                data: { username: 'testuser', email: 'test@example.com' },
            });
            // Warmup mock
            api.post.mockResolvedValueOnce({ data: { status: 'warming' } });

            await act(async () => {
                await result.current.login('testuser', 'password123');
            });

            // Check that warmup was called (second post call)
            expect(api.post).toHaveBeenCalledTimes(2);
            expect(api.post).toHaveBeenNthCalledWith(2, '/recipes/warmup');
        });

        it('should handle login failure', async () => {
            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            await waitFor(() => expect(result.current.loading).toBe(false));

            api.post.mockRejectedValueOnce(new Error('Invalid credentials'));

            await expect(
                act(async () => {
                    await result.current.login('wrong', 'credentials');
                })
            ).rejects.toThrow('Invalid credentials');

            expect(result.current.user).toBeNull();
            expect(localStorage.getItem('token')).toBeNull();
        });
    });

    describe('register', () => {
        it('should register and login new user', async () => {
            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            await waitFor(() => expect(result.current.loading).toBe(false));

            // Register mock
            api.post.mockResolvedValueOnce({ data: { message: 'User created' } });
            // Login mock (called by register)
            api.post.mockResolvedValueOnce({
                data: { access_token: 'new_token', token_type: 'bearer' },
            });
            // Profile fetch
            api.get.mockResolvedValueOnce({
                data: { username: 'newuser', email: 'new@example.com' },
            });
            // Warmup
            api.post.mockResolvedValueOnce({ data: { status: 'warming' } });

            await act(async () => {
                await result.current.register('newuser', 'new@example.com', 'password');
            });

            expect(result.current.user).toEqual({
                username: 'newuser',
                email: 'new@example.com',
            });
            expect(localStorage.getItem('token')).toBe('new_token');
        });
    });

    describe('logout', () => {
        it('should clear user and token on logout', async () => {
            localStorage.setItem('token', 'test_token');

            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            await waitFor(() => expect(result.current.loading).toBe(false));

            act(() => {
                result.current.logout();
            });

            expect(result.current.user).toBeNull();
            expect(localStorage.getItem('token')).toBeNull();
        });
    });

    describe('token persistence', () => {
        it('should restore user from stored token on mount', async () => {
            // Reset all mocks first to clear the beforeEach reject mock
            vi.clearAllMocks();

            localStorage.setItem('token', 'stored_token');

            // Mock profile fetch - this should be called when checking stored token
            api.get.mockResolvedValue({
                data: {
                    username: 'storeduser',
                    email: 'stored@example.com',
                },
            });
            // Mock warmup (fire-and-forget, may be called)
            api.post.mockResolvedValue({ data: { status: 'warming' } });

            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            await waitFor(() => expect(result.current.loading).toBe(false), { timeout: 3000 });

            expect(result.current.user).toEqual({
                username: 'storeduser',
                email: 'stored@example.com',
            });
        });

        it('should clear invalid token on mount', async () => {
            localStorage.setItem('token', 'invalid_token');

            api.get.mockRejectedValueOnce(new Error('Invalid token'));

            const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;
            const { result } = renderHook(() => useAuth(), { wrapper });

            await waitFor(() => expect(result.current.loading).toBe(false));

            expect(result.current.user).toBeNull();
            expect(localStorage.getItem('token')).toBeNull();
        });
    });
});
