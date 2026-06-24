import React, { useState, useEffect } from 'react';

export default function AddProspectModal({ list, isOpen, onClose, onSuccess }) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [domain, setDomain] = useState('');
  const [errors, setErrors] = useState({});
  
  // Status: 'idle' | 'loading' | 'success' | 'error'
  const [status, setStatus] = useState('idle');
  const [statusTitle, setStatusTitle] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [resolvedEmail, setResolvedEmail] = useState('');
  
  // Stepper tracking for visual progression
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (isOpen) {
      setFirstName('');
      setLastName('');
      setDomain('');
      setErrors({});
      setStatus('idle');
      setCurrentStep(0);
    }
  }, [isOpen]);

  if (!isOpen || !list) return null;

  const validate = () => {
    const newErrors = {};
    
    if (!firstName.trim()) {
      newErrors.firstName = 'First name is required';
    } else if (/\d/.test(firstName)) {
      newErrors.firstName = 'First name cannot contain numbers';
    }

    if (!lastName.trim()) {
      newErrors.lastName = 'Last name is required';
    } else if (/\d/.test(lastName)) {
      newErrors.lastName = 'Last name cannot contain numbers';
    }

    if (!domain.trim()) {
      newErrors.domain = 'Company domain or name is required';
    } else if (domain.trim().length < 2) {
      newErrors.domain = 'Company domain or name must be at least 2 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setStatus('loading');
    
    // Simulate steps to make the asynchronous process visually rich and clear
    setCurrentStep(0); // Validating details
    
    const incrementStep = (step, delay) => {
      return new Promise((resolve) => {
        setTimeout(() => {
          setCurrentStep(step);
          resolve();
        }, delay);
      });
    };

    // Trigger sequential UI steps
    const step1Promise = incrementStep(1, 800);  // "Checking Snov.io authorization..."
    const step2Promise = step1Promise.then(() => incrementStep(2, 1200)); // "Finding business email address..."

    // Call API in parallel
    try {
      let cleanedDomain = domain.trim().toLowerCase();
      if (cleanedDomain.startsWith('http://')) cleanedDomain = cleanedDomain.slice(7);
      if (cleanedDomain.startsWith('https://')) cleanedDomain = cleanedDomain.slice(8);
      if (cleanedDomain.startsWith('www.')) cleanedDomain = cleanedDomain.slice(4);

      const apiPromise = fetch('/api/prospects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          list_id: list.id,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          domain: cleanedDomain,
        }),
      });

      // Wait for step animations and API response
      const [_, response] = await Promise.all([step2Promise, apiPromise]);
      const data = await response.json();

      if (response.ok) {
        // Complete last step
        setCurrentStep(3); // "Adding prospect to list"
        await incrementStep(4, 800); // Wait briefly
        
        setResolvedEmail(data.email);
        setStatusTitle('Success!');
        setStatusMessage(data.message);
        setStatus('success');
        onSuccess(); // Trigger list reload
      } else {
        setStatusTitle('Resolving Failed');
        setStatusMessage(data.detail || 'An error occurred during lookup.');
        setStatus('error');
      }
    } catch (err) {
      console.error(err);
      setStatusTitle('Lookup Failed');
      setStatusMessage('Could not connect to the backend server. Make sure the backend server is running on port 8000.');
      setStatus('error');
    }
  };

  return (
    <div className="modal-overlay" onClick={status === 'loading' ? undefined : onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {status !== 'loading' && (
          <button className="modal-close" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        )}

        {status === 'idle' && (
          <>
            <h2 className="modal-title">Add Prospect</h2>
            <p className="modal-subtitle">
              Adding to list: <strong style={{ color: 'var(--primary)' }}>{list.name}</strong>
            </p>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label" htmlFor="first-name">First Name</label>
                <input
                  id="first-name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. John"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
                {errors.firstName && <span className="form-error-msg">{errors.firstName}</span>}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="last-name">Last Name</label>
                <input
                  id="last-name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Doe"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
                {errors.lastName && <span className="form-error-msg">{errors.lastName}</span>}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="company-domain">Company Domain or Name</label>
                <input
                  id="company-domain"
                  type="text"
                  className="form-input"
                  placeholder="e.g. stripe.com or Stripe"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                />
                {errors.domain && <span className="form-error-msg">{errors.domain}</span>}
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={onClose}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Find & Add Prospect
                </button>
              </div>
            </form>
          </>
        )}

        {status === 'loading' && (
          <div className="modal-status-screen">
            <div className="status-spinner" />
            <h3 className="status-title">Searching for Prospect</h3>
            <p className="status-desc">
              Looking up domain details and finding matching email addresses...
            </p>

            <div className="stepper">
              <div className={`step-item ${currentStep === 0 ? 'active' : ''} ${currentStep > 0 ? 'completed' : ''}`}>
                <div className="step-dot" />
                <span>Validating prospect details...</span>
              </div>
              <div className={`step-item ${currentStep === 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}>
                <div className="step-dot" />
                <span>Checking Snov.io authorization...</span>
              </div>
              <div className={`step-item ${currentStep === 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}`}>
                <div className="step-dot" />
                <span>Finding business email address...</span>
              </div>
              <div className={`step-item ${currentStep === 3 ? 'active' : ''} ${currentStep > 3 ? 'completed' : ''}`}>
                <div className="step-dot" />
                <span>Adding prospect to list...</span>
              </div>
            </div>
          </div>
        )}

        {status === 'success' && (
          <div className="modal-status-screen">
            <div className="status-icon-success">✓</div>
            <h3 className="status-title" style={{ color: 'var(--success)' }}>{statusTitle}</h3>
            <p className="status-desc">{statusMessage}</p>
            <div style={{
              background: 'rgba(255,255,255,0.03)',
              padding: '12px 18px',
              borderRadius: '8px',
              border: '1px solid var(--border-glass)',
              fontSize: '14px',
              marginBottom: '24px',
              width: '100%',
              textAlign: 'center'
            }}>
              Resolved Email: <strong style={{ color: 'var(--primary)' }}>{resolvedEmail}</strong>
            </div>
            <button className="btn btn-primary" onClick={onClose} style={{ width: '100%' }}>
              Done
            </button>
          </div>
        )}

        {status === 'error' && (
          <div className="modal-status-screen">
            <div className="status-icon-error">✕</div>
            <h3 className="status-title" style={{ color: 'var(--error)' }}>{statusTitle}</h3>
            <p className="status-desc">{statusMessage}</p>
            <div className="modal-footer" style={{ width: '100%', marginTop: '10px' }}>
              <button className="btn btn-secondary" onClick={onClose} style={{ flex: 1 }}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={() => setStatus('idle')} style={{ flex: 1 }}>
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
