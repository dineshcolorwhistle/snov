import React, { useState, useEffect } from 'react';
import { apiFetch } from '../utils/api';

function parseCSV(text) {
  const lines = [];
  let row = [""];
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        row[row.length - 1] += '"';
        i++; // skip next quote
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      row.push("");
    } else if ((char === '\r' || char === '\n') && !inQuotes) {
      if (char === '\r' && nextChar === '\n') {
        i++;
      }
      lines.push(row);
      row = [""];
    } else {
      row[row.length - 1] += char;
    }
  }
  if (row.length > 1 || row[0] !== "") {
    lines.push(row);
  }
  return lines;
}

const makeCSVBlob = (batchRows) => {
  const headerLine = '"First Name","Last Name","Company Name","Location","Title"';
  const rowLines = batchRows.map(row => 
    `"${row["First Name"].replace(/"/g, '""')}","${row["Last Name"].replace(/"/g, '""')}","${row["Company Name"].replace(/"/g, '""')}","${(row["Location"] || "").replace(/"/g, '""')}","${(row["Title"] || "").replace(/"/g, '""')}"`
  );
  const csvText = [headerLine, ...rowLines].join('\n');
  return new Blob([csvText], { type: 'text/csv' });
};

export default function AddProspectModal({ list, isOpen, onClose, onSuccess, lists = [] }) {
  const activePlatform = localStorage.getItem('active_platform') || 'snov';
  const platformName = activePlatform === 'snov' ? 'Snov.io' : 'Hunter.io';

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [location, setLocation] = useState('');
  const [title, setTitle] = useState('');
  const [errors, setErrors] = useState({});
  
  // Tabs: 'single' | 'csv'
  const [activeTab, setActiveTab] = useState('single');
  
  // CSV File Upload states
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [bulkResults, setBulkResults] = useState(null);
  const [verifyEmails, setVerifyEmails] = useState(true);
  const [unverifiedListId, setUnverifiedListId] = useState('');

  // Batching & progress tracking states
  const [progress, setProgress] = useState(0);
  const [totalProspects, setTotalProspects] = useState(0);
  const [processedProspects, setProcessedProspects] = useState(0);

  // Status: 'idle' | 'loading' | 'success' | 'bulk-success' | 'error'
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
      setCompanyName('');
      setLocation('');
      setTitle('');
      setErrors({});
      setStatus('idle');
      setCurrentStep(0);
      setActiveTab('single');
      setFile(null);
      setDragActive(false);
      setBulkResults(null);
      setVerifyEmails(true);
      setUnverifiedListId('');
      setProgress(0);
      setTotalProspects(0);
      setProcessedProspects(0);
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

    if (!companyName.trim()) {
      newErrors.companyName = 'Company name is required';
    } else if (companyName.trim().length < 2) {
      newErrors.companyName = 'Company name must be at least 2 characters';
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
    const step1Promise = incrementStep(1, 800);  // Checking authorization
    const step2Promise = step1Promise.then(() => incrementStep(2, 1200)); // Finding business email address

    // Call API in parallel
    try {
      let cleanedCompanyName = companyName.trim();

      const apiPromise = apiFetch('/api/prospects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          list_id: list.id,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          company_name: cleanedCompanyName,
          location: location.trim() || null,
          title: title.trim() || null,
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

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile);
        setErrors({});
      } else {
        setErrors({ file: 'Only CSV files are supported' });
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.name.endsWith('.csv')) {
        setFile(selectedFile);
        setErrors({});
      } else {
        setErrors({ file: 'Only CSV files are supported' });
      }
    }
  };

  const handleBulkSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setErrors({ file: 'Please upload a CSV file' });
      return;
    }
    if (verifyEmails && !unverifiedListId) {
      setErrors({ unverifiedList: 'Please select a list for unverified email addresses' });
      return;
    }
    
    const reader = new FileReader();
    reader.onerror = () => {
      setErrors({ file: 'Failed to read CSV file.' });
    };
    reader.onload = async (event) => {
      const text = event.target.result;
      
      let parsed;
      try {
        parsed = parseCSV(text);
        if (parsed.length === 0 || (parsed.length === 1 && parsed[0].length === 1 && parsed[0][0] === "")) {
          throw new Error("CSV file is empty.");
        }
      } catch (err) {
        setErrors({ file: err.message || 'Failed to parse CSV file.' });
        return;
      }
      
      const headers = parsed[0].map(h => h.trim());
      
      // Normalize headers to support synonyms case-insensitively
      const normalizedHeaders = headers.map(h => {
        const lower = h.toLowerCase();
        if (lower === 'first name') return 'First Name';
        if (lower === 'last name' || lower === 'last-name') return 'Last Name';
        if (
          lower === 'company domain/name' || 
          lower === 'company name / domain' || 
          lower === 'company name/domain' || 
          lower === 'company domain or name' ||
          lower === 'company name or domain' ||
          lower === 'company name' ||
          lower === 'company domain' ||
          lower === 'domain'
        ) {
          return 'Company Name';
        }
        if (lower === 'location') return 'Location';
        if (lower === 'title') return 'Title';
        return h;
      });

      const expectedHeaders = ['First Name', 'Last Name', 'Company Name', 'Location', 'Title'];
      
      // Enforce that all required headers are present
      const missingHeaders = expectedHeaders.filter(eh => !normalizedHeaders.includes(eh));
      if (missingHeaders.length > 0) {
        setErrors({ file: `The CSV file is missing required headers: ${missingHeaders.join(', ')}. Required: First Name, Last Name, Company Name, Location, Title.` });
        return;
      }
      
      // Extract rows
      const rows = [];
      for (let i = 1; i < parsed.length; i++) {
        const rowData = parsed[i];
        if (rowData.length < 3) continue;
        
        const rowObj = {};
        normalizedHeaders.forEach((header, index) => {
          // Only map required headers (ignore extras, especially when >10 columns)
          if (expectedHeaders.includes(header)) {
            rowObj[header] = rowData[index] || "";
          }
        });
        
        // Skip if completely blank row
        if (!rowObj["First Name"].trim() && !rowObj["Last Name"].trim() && !rowObj["Company Name"].trim()) {
          continue;
        }
        
        rows.push(rowObj);
      }
      
      if (rows.length === 0) {
        setErrors({ file: "CSV file has no valid prospect records." });
        return;
      }
      
      // We have valid rows! Let's start progress tracking
      setStatus('loading');
      setTotalProspects(rows.length);
      setProcessedProspects(0);
      setProgress(0);
      
      // Chunk size of 5
      const chunkSize = 5;
      const chunks = [];
      for (let i = 0; i < rows.length; i += chunkSize) {
        chunks.push(rows.slice(i, i + chunkSize));
      }
      
      const accumulatedResults = {
        total: rows.length,
        successCount: 0,
        failedCount: 0,
        failedRecords: []
      };
      
      let currentProcessed = 0;
      
      try {
        for (let batchIndex = 0; batchIndex < chunks.length; batchIndex++) {
          const batch = chunks[batchIndex];
          const csvBlob = makeCSVBlob(batch);
          
          const formData = new FormData();
          formData.append('list_id', list.id);
          if (verifyEmails) {
            formData.append('unverified_list_id', unverifiedListId);
          }
          formData.append('file', csvBlob, 'batch.csv');
          formData.append('verify_emails', verifyEmails);
          
          const response = await apiFetch('/api/prospects/bulk', {
            method: 'POST',
            body: formData,
          });
          const data = await response.json();
          
          if (!response.ok) {
            const failReason = data.detail || 'Connection error processing batch.';
            batch.forEach(row => {
              accumulatedResults.failedCount++;
              accumulatedResults.failedRecords.push({
                first_name: row["First Name"] || "[Blank]",
                last_name: row["Last Name"] || "[Blank]",
                company: row["Company Name"] || "[Blank]",
                reason: failReason
              });
            });
          } else {
            accumulatedResults.successCount += data.successCount;
            accumulatedResults.failedCount += data.failedCount;
            accumulatedResults.failedRecords.push(...data.failedRecords);
          }
          
          currentProcessed += batch.length;
          setProcessedProspects(currentProcessed);
          setProgress(Math.round((currentProcessed / rows.length) * 100));
        }
        
        // Complete processing!
        setBulkResults(accumulatedResults);
        setStatus('bulk-success');
        onSuccess();
      } catch (err) {
        console.error(err);
        setStatusTitle('Import Failed');
        setStatusMessage('Could not connect to the backend server. Make sure the backend server is running on port 8000.');
        setStatus('error');
      }
    };
    reader.readAsText(file);
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

            <div className="modal-tabs">
              <button 
                type="button"
                className={`modal-tab ${activeTab === 'single' ? 'active' : ''}`}
                onClick={() => {
                  setActiveTab('single');
                  setErrors({});
                }}
              >
                Single Prospect
              </button>
              <button 
                type="button"
                className={`modal-tab ${activeTab === 'csv' ? 'active' : ''}`}
                onClick={() => {
                  setActiveTab('csv');
                  setErrors({});
                }}
              >
                Upload CSV
              </button>
            </div>

            {activeTab === 'single' ? (
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
                  <label className="form-label" htmlFor="company-name">Company Name</label>
                  <input
                    id="company-name"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Stripe"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                  />
                  {errors.companyName && <span className="form-error-msg">{errors.companyName}</span>}
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="prospect-location">Location</label>
                  <input
                    id="prospect-location"
                    type="text"
                    className="form-input"
                    placeholder="e.g. San Francisco, CA"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="prospect-title">Title</label>
                  <input
                    id="prospect-title"
                    type="text"
                    className="form-input"
                    placeholder="e.g. VP of Engineering"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
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
            ) : (
              <form onSubmit={handleBulkSubmit}>
                <div 
                  className={`file-drop-zone ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => !file && document.getElementById('file-input').click()}
                >
                  <input 
                    id="file-input"
                    type="file"
                    accept=".csv"
                    style={{ display: 'none' }}
                    onChange={handleFileChange}
                  />
                  
                  {file ? (
                    <div className="file-info-container">
                      <div className="file-icon">📄</div>
                      <div className="file-details">
                        <span className="file-name">{file.name}</span>
                        <span className="file-size">{(file.size / 1024).toFixed(2)} KB</span>
                      </div>
                      <button 
                        type="button" 
                        className="file-remove-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                        }}
                        aria-label="Remove file"
                      >
                        &times;
                      </button>
                    </div>
                  ) : (
                    <div className="drop-zone-prompt">
                      <div className="upload-icon">📥</div>
                      <p className="drop-text">Drag & drop your CSV file here, or <span className="browse-link">browse</span></p>
                      <p className="drop-subtext">Supports only one CSV file</p>
                    </div>
                  )}
                </div>
                {errors.file && <span className="form-error-msg" style={{ display: 'block', marginTop: '8px', textAlign: 'center' }}>{errors.file}</span>}

                <div className="toggle-container">
                  <div style={{ flexGrow: 1, textAlign: 'left' }}>
                    <span className="toggle-label" onClick={() => setVerifyEmails(!verifyEmails)}>Verify Emails</span>
                    <div className="toggle-sublabel">Verify email addresses before adding them to the list (recommended)</div>
                  </div>
                  <label className="toggle-switch">
                    <input 
                      type="checkbox" 
                      checked={verifyEmails} 
                      onChange={(e) => setVerifyEmails(e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                {verifyEmails && (
                  <div className="form-group" style={{ marginTop: '16px', textAlign: 'left' }}>
                    <label className="form-label" htmlFor="unverified-list-select">
                      Unverified Prospects List
                    </label>
                    <select
                      id="unverified-list-select"
                      className="form-input"
                      value={unverifiedListId}
                      onChange={(e) => {
                        setUnverifiedListId(e.target.value);
                        if (errors.unverifiedList) {
                          setErrors(prev => ({ ...prev, unverifiedList: null }));
                        }
                      }}
                    >
                      <option value="">-- Select a list for unverified emails --</option>
                      {lists
                        .filter((l) => l.id !== list.id)
                        .map((l) => (
                          <option key={l.id} value={l.id}>
                            {l.name}
                          </option>
                        ))}
                    </select>
                    {errors.unverifiedList && (
                      <span className="form-error-msg">{errors.unverifiedList}</span>
                    )}
                  </div>
                )}

                <div className="upload-note">
                  <strong>Note:</strong> The CSV file must contain these five headers:
                  <ul>
                    <li>First Name</li>
                    <li>Last Name</li>
                    <li>Company Name</li>
                    <li>Location</li>
                    <li>Title</li>
                  </ul>
                </div>

                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={onClose}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={!file}>
                    Process CSV
                  </button>
                </div>
              </form>
            )}
          </>
        )}

        {status === 'loading' && (
          <div className="modal-status-screen">
            <div className="status-spinner" />
            <h3 className="status-title">
              {activeTab === 'csv' ? 'Processing CSV File' : 'Searching for Prospect'}
            </h3>
            <p className="status-desc">
              {activeTab === 'csv' 
                ? 'Finding domains, looking up business email addresses, and adding leads...'
                : 'Looking up domain details and finding matching email addresses...'
              }
            </p>

            {activeTab === 'csv' && (
              <div className="progress-container">
                <div className="progress-bar-bg">
                  <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
                </div>
                <div className="progress-text">
                  Processing {processedProspects} of {totalProspects} prospects ({progress}%)...
                </div>
              </div>
            )}

            {activeTab === 'single' && (
              <div className="stepper">
                <div className={`step-item ${currentStep === 0 ? 'active' : ''} ${currentStep > 0 ? 'completed' : ''}`}>
                  <div className="step-dot" />
                  <span>Validating prospect details...</span>
                </div>
                <div className={`step-item ${currentStep === 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}>
                  <div className="step-dot" />
                  <span>Checking {platformName} authorization...</span>
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
            )}
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

        {status === 'bulk-success' && bulkResults && (
          <div className="modal-status-screen bulk-results-screen">
            <div className={bulkResults.failedCount > 0 ? "status-icon-warning" : "status-icon-success"}>
              {bulkResults.failedCount > 0 ? "⚠" : "✓"}
            </div>
            <h3 className="status-title" style={{ color: bulkResults.failedCount > 0 ? 'var(--warning)' : 'var(--success)' }}>
              {bulkResults.failedCount > 0 ? 'Import Completed with Failures' : 'Import Completed Successfully!'}
            </h3>
            
            <div className="bulk-stats-grid">
              <div className="bulk-stat-card">
                <span className="stat-label">Processed</span>
                <span className="stat-val">{bulkResults.total}</span>
              </div>
              <div className="bulk-stat-card success">
                <span className="stat-label">Success</span>
                <span className="stat-val">{bulkResults.successCount}</span>
              </div>
              <div className="bulk-stat-card error">
                <span className="stat-label">Failed</span>
                <span className="stat-val">{bulkResults.failedCount}</span>
              </div>
            </div>

            {bulkResults.failedCount > 0 && (
              <div className="failed-records-container">
                <div className="failed-records-header">Failed Records Details</div>
                <div className="failed-records-list">
                  {bulkResults.failedRecords.map((rec, idx) => (
                    <div key={idx} className="failed-record-item">
                      <div className="failed-record-info">
                        <span className="failed-record-name">{rec.first_name} {rec.last_name}</span>
                        <span className="failed-record-company">{rec.company}</span>
                      </div>
                      <div className="failed-record-reason">{rec.reason}</div>
                    </div>
                  ))}
                </div>
                <p className="failed-records-footer-note">
                  * Failed entries were routed to the fallback <strong>email-not-found-cw1</strong> list.
                </p>
              </div>
            )}

            <button className="btn btn-primary" onClick={onClose} style={{ width: '100%', marginTop: '16px' }}>
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
