import React, { createContext, useState, useEffect, useContext } from 'react';
import api from '../api/axios';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const checkLoggedIn = async () => {
            const token = localStorage.getItem('token');
            if (token) {
                try {
                    // Verify token by fetching profile
                    const response = await api.get('/users/profile');
                    setUser(response.data);
                } catch (error) {
                    localStorage.removeItem('token');
                    setUser(null);
                }
            }
            setLoading(false);
        };
        checkLoggedIn();
    }, []);

    const login = async (username, password) => {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await api.post('/auth/token', formData);
        const { access_token } = response.data;

        localStorage.setItem('token', access_token);

        // Fetch profile immediately
        const profileRes = await api.get('/users/profile');
        setUser(profileRes.data);

        // 🔥 Warmup: Fire-and-forget request to wake up LLM service
        // This reduces cold start latency for first recipe generation
        // Don't await - let it happen in background, silently ignore failures
        api.post('/recipes/warmup').catch(() => {
            // Silent ignore - warmup is optional, shouldn't break login
        });

        return true;
    };

    const register = async (username, email, password) => {
        await api.post('/auth/register', { username, email, password });
        return login(username, password);
    };

    const logout = () => {
        localStorage.removeItem('token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, register, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
