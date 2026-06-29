import React, { useState, useEffect } from 'react';
import { apiFetch } from '../utils/api';

export default function SettingsModal({ isOpen, onClose, onSaveSuccess }) {
  const [snovClientId, setSnovClientId] = useState('');
  const [snovClientSecret, setSnovClientSecret] = useState('');
  const [hunterApiKey, setHunterApiKey] = useState('');
  const [emailNotFoundListId, setEmailNotFoundListId] = useState('');
  const [hunterFallbackListId, setHunterFallbackListId] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
    } else {
      setError('');
      setSuccessMsg('');
    }
  }, [isOpen]);

  const fetchSettings = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await apiFetch('/api/settings');
      const data = await response.json();
      if (response.ok && data.success) {
        const s = data.settings || {};
        setSnovClientId(s.snov_client_id || '');
        setSnovClientSecret(s.snov_client_secret || '');
        setHunterApiKey(s.hunter_api_key || '');
        setEmailNotFoundListId(s.email_not_found_list_id || '');
        setHunterFallbackListId(s.hunter_fallback_list_id || '');
      } else {
        setError(data.detail || 'Failed to load settings.');
      }
    } catch (err) {
      console.error(err);
      setError('Could not connect to the server.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setError('');
    setSuccessMsg('');
    try {
      const response = await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          snov_client_id: snovClientId.trim(),
          snov_client_secret: snovClientSecret.trim(),
          hunter_api_key: hunterApiKey.trim(),
          email_not_found_list_id: emailNotFoundListId.trim(),
          hunter_fallback_list_id: hunterFallbackListId.trim()
        })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setSuccessMsg('Settings saved successfully!');
        if (onSaveSuccess) onSaveSuccess();
        setTimeout(() => {
          onClose();
        }, 1500);
      } else {
        setError(data.detail || 'Failed to save settings.');
      }
    } catch (err) {
      console.error(err);
      setError('Could not connect to the server.');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px', width: '90%' }}>
        <button className="modal-close" onClick={onClose} aria-label="Close settings">
          &times;
        </button>
        <h2 className="modal-title">API Credentials & Settings</h2>
        <p className="modal-subtitle">
          Configure your platform API keys. These settings are saved securely in your Supabase account.
        </p>

        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 0' }}>
            <div className="status-spinner"></div>
            <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>Loading settings...</p>
          </div>
        ) : (
          <form onSubmit={handleSave}>
            {error && (
              <div className="login-error" style={{ marginBottom: '16px' }}>
                <span className="login-error-icon">✕</span>
                <span>{error}</span>
              </div>
            )}

            {successMsg && (
              <div style={{
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                color: 'var(--success)',
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '14px'
              }}>
                <span>✓</span>
                <span>{successMsg}</span>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Snov.io Settings */}
              <div style={{
                border: '1px solid var(--border-glass)',
                padding: '16px',
                borderRadius: '12px',
                background: 'rgba(255, 255, 255, 0.01)'
              }}>
                <h3 style={{ fontSize: '15px', color: '#a78bfa', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ background: '#a78bfa', color: '#000', borderRadius: '4px', width: '18px', height: '18px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: 'bold' }}>S</span>
                  Snov.io API Configuration
                </h3>
                
                <div className="form-group">
                  <label className="form-label">Snov.io Client ID</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Enter Snov.io Client ID"
                    value={snovClientId}
                    onChange={(e) => setSnovClientId(e.target.value)}
                  />
                </div>

                <div className="form-group" style={{ marginTop: '12px' }}>
                  <label className="form-label">Snov.io Client Secret</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="Enter Snov.io Client Secret"
                    value={snovClientSecret}
                    onChange={(e) => setSnovClientSecret(e.target.value)}
                  />
                </div>
              </div>

              {/* Hunter.io Settings */}
              <div style={{
                border: '1px solid var(--border-glass)',
                padding: '16px',
                borderRadius: '12px',
                background: 'rgba(255, 255, 255, 0.01)'
              }}>
                <h3 style={{ fontSize: '15px', color: '#f59e0b', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ background: '#f59e0b', color: '#000', borderRadius: '4px', width: '18px', height: '18px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: 'bold' }}>H</span>
                  Hunter.io API Configuration
                </h3>
                
                <div className="form-group">
                  <label className="form-label">Hunter.io API Key</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="Enter Hunter.io API Key"
                    value={hunterApiKey}
                    onChange={(e) => setHunterApiKey(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="modal-footer" style={{ marginTop: '24px' }}>
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={isSaving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={isSaving}>
                {isSaving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
