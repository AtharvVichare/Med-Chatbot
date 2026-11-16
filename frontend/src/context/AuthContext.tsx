import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../types';
import { api } from '../services/api';

interface SignupPayload {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  gender: string;
  date_of_birth: string;
  phone?: string;
  district?: string;
  state?: string;
  is_smoker?: boolean;
  blood_group?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  googleLogin: (idToken: string) => Promise<void>;
  signup: (payload: SignupPayload) => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const savedUser = localStorage.getItem('aarogya_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('aarogya_jwt');
  });

  useEffect(() => {
    const handleLogoutEvent = () => {
      logout();
    };
    window.addEventListener('auth_logout', handleLogoutEvent);
    return () => window.removeEventListener('auth_logout', handleLogoutEvent);
  }, []);

  const login = async (username: string, password: string) => {
    const response = await api.login(username, password);
    const loggedUser: User = {
      username: response.username,
      role: response.role,
      full_name: response.full_name,
      patient_id: response.patient_id,
      gender: response.gender,
      date_of_birth: response.date_of_birth
    };

    setToken(response.access_token);
    setUser(loggedUser);
    localStorage.setItem('aarogya_jwt', response.access_token);
    localStorage.setItem('aarogya_user', JSON.stringify(loggedUser));
  };

  const googleLogin = async (idToken: string) => {
    const response = await api.googleLogin(idToken);
    const loggedUser: User = {
      username: response.username,
      role: response.role,
      full_name: response.full_name,
      patient_id: response.patient_id,
      gender: response.gender,
      date_of_birth: response.date_of_birth
    };

    setToken(response.access_token);
    setUser(loggedUser);
    localStorage.setItem('aarogya_jwt', response.access_token);
    localStorage.setItem('aarogya_user', JSON.stringify(loggedUser));
  };

  const signup = async (payload: SignupPayload) => {
    const response = await api.signup(payload);
    const loggedUser: User = {
      username: response.username,
      role: response.role,
      full_name: response.full_name,
      patient_id: response.patient_id,
      gender: response.gender || payload.gender,
      date_of_birth: response.date_of_birth || payload.date_of_birth
    };

    setToken(response.access_token);
    setUser(loggedUser);
    localStorage.setItem('aarogya_jwt', response.access_token);
    localStorage.setItem('aarogya_user', JSON.stringify(loggedUser));
  };

  const updateUser = (updates: Partial<User>) => {
    setUser(prev => {
      if (!prev) return null;
      const updated = { ...prev, ...updates };
      localStorage.setItem('aarogya_user', JSON.stringify(updated));
      return updated;
    });
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('aarogya_jwt');
    localStorage.removeItem('aarogya_user');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, googleLogin, signup, updateUser, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
