import React, { useState, useEffect } from 'react';
import { getSupabase, initializeSupabase } from '../utils/supabaseClient';

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [supabaseAnonKey, setSupabaseAnonKey] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Check if anon key is configured in env or localStorage
  const hasEnvAnonKey = !!import.meta.env.VITE_SUPABASE_ANON_KEY;
  const [needsAnonKey, setNeedsAnonKey] = useState(false);

  useEffect(() => {
    const supabase = getSupabase();
    setNeedsAnonKey(!supabase && !hasEnvAnonKey);
  }, [hasEnvAnonKey]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Both email and password are required');
      return;
    }
    
    if (needsAnonKey && !supabaseAnonKey.trim()) {
      setError('Supabase Anon Key is required to connect to your project');
      return;
    }

    setError('');
    setIsLoading(true);
    try {
      let supabase = getSupabase();
      
      // If we need to initialize dynamically
      if (needsAnonKey && supabaseAnonKey.trim()) {
        supabase = initializeSupabase(supabaseAnonKey.trim());
      }
      
      if (!supabase) {
        throw new Error('Supabase client is not initialized. Please configure VITE_SUPABASE_ANON_KEY in your frontend/.env file.');
      }

      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password: password,
      });

      if (authError) {
        setError(authError.message);
      } else if (data && data.session) {
        const userPayload = {
          email: data.user.email,
          name: data.user.user_metadata?.name || data.user.user_metadata?.full_name || data.user.email.split('@')[0].toUpperCase(),
          id: data.user.id
        };
        onLoginSuccess(data.session.access_token, userPayload);
      } else {
        setError('Login failed. Please check your credentials.');
      }
    } catch (err) {
      console.error(err);
      setError(err.message || 'Could not connect to Supabase');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page-wrapper">
      <div className="login-card">
        <div className="login-logo">
          <span className="logo-icon">S</span>
          <span className="logo-text">LeadFlow</span>
          <span className="logo-badge">Automation</span>
        </div>
        <h2 className="login-title">Sign In</h2>
        <p className="login-subtitle">Enter your Supabase credentials to access the dashboard</p>
        
        {error && (
          <div className="login-error">
            <span className="login-error-icon">✕</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {needsAnonKey && (
            <div className="form-group" style={{ background: 'rgba(245, 158, 11, 0.05)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.2)', marginBottom: '16px' }}>
              <label className="form-label" htmlFor="login-anon-key" style={{ color: '#f59e0b', fontWeight: 'bold' }}>
                Supabase Anon Key *
              </label>
              <input
                id="login-anon-key"
                type="password"
                className="form-input"
                placeholder="Paste your Supabase Project Anon Key"
                value={supabaseAnonKey}
                onChange={(e) => setSupabaseAnonKey(e.target.value)}
                required
                disabled={isLoading}
                style={{ borderColor: 'rgba(245, 158, 11, 0.4)' }}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginTop: '4px' }}>
                Found in Supabase Dashboard -> Project Settings -> API
              </span>
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="login-email">Email Address</label>
            <input
              id="login-email"
              type="email"
              className="form-input"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label" htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary login-btn"
            disabled={isLoading}
            style={{ width: '100%', padding: '12px 20px', fontSize: '15px' }}
          >
            {isLoading ? (
              <>
                <svg 
                  className="login-spinner" 
                  width="16" 
                  height="16" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="3" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                  style={{ animation: 'spin 1s linear infinite' }}
                >
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                </svg>
                Connecting to Supabase...
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
