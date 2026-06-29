import React, { useState, useEffect } from 'react';
import { apiFetch } from '../utils/api';

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return dateStr.split('T')[0] || dateStr;
  }
};

export default function TrackingLogs({ activePlatform }) {
  // Tabs: 'linkedin_not_found' | 'domain_not_found' | 'email_not_found' | 'email_unverified'
  const [activeTab, setActiveTab] = useState('linkedin_not_found');
  const [logs, setLogs] = useState([]);
  const [totalLogs, setTotalLogs] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Pagination
  const [page, setPage] = useState(1);
  const limit = 10;

  useEffect(() => {
    fetchLogs();
  }, [activeTab, activePlatform, page]);

  // Reset page when switching tabs or platforms
  useEffect(() => {
    setPage(1);
  }, [activeTab, activePlatform]);

  const fetchLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/logs/${activeTab}?platform=${activePlatform}&page=${page}&limit=${limit}`);
      const data = await response.json();
      if (response.ok && data.success) {
        setLogs(data.logs || []);
        setTotalLogs(data.total || 0);
      } else {
        setError(data.detail || 'Failed to fetch tracking logs.');
      }
    } catch (err) {
      console.error(err);
      setError('Could not connect to the server.');
    } finally {
      setIsLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalLogs / limit));

  const tabLabels = {
    linkedin_not_found: 'Missing LinkedIn',
    domain_not_found: 'Missing Domains',
    email_not_found: 'Missing Emails',
    email_unverified: 'Unverified Emails'
  };

  return (
    <div className="tracking-logs-container" style={{ marginTop: '24px' }}>
      {/* Sub tabs for log types */}
      <div className="modal-tabs" style={{ marginBottom: '20px', borderBottom: '1px solid var(--border-glass)' }}>
        {Object.entries(tabLabels).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`modal-tab ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
            style={{ padding: '12px 20px', fontSize: '14px' }}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.2)',
          color: 'var(--error)',
          padding: '16px',
          borderRadius: '12px',
          textAlign: 'center',
          marginBottom: '20px'
        }}>
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={fetchLogs} style={{ marginTop: '12px' }}>
            Retry
          </button>
        </div>
      ) : (
        <div className="prospects-table-container" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-glass)', borderRadius: '16px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '16px', color: 'var(--text-primary)' }}>
              {tabLabels[activeTab]} ({totalLogs} total)
            </h3>
            <button 
              className="btn btn-secondary" 
              onClick={fetchLogs}
              disabled={isLoading}
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              Refresh Logs
            </button>
          </div>

          <table className="prospects-table">
            <thead>
              {activeTab === 'linkedin_not_found' && (
                <tr>
                  <th>First Name</th>
                  <th>Last Name</th>
                  <th>Company Name</th>
                  <th>Logged Date</th>
                </tr>
              )}
              {activeTab === 'domain_not_found' && (
                <tr>
                  <th>First Name</th>
                  <th>Last Name</th>
                  <th>Company Name</th>
                  <th>LinkedIn Profile</th>
                  <th>Logged Date</th>
                </tr>
              )}
              {activeTab === 'email_not_found' && (
                <tr>
                  <th>First Name</th>
                  <th>Last Name</th>
                  <th>Company Name</th>
                  <th>Resolved Domain</th>
                  <th>LinkedIn Profile</th>
                  <th>Logged Date</th>
                </tr>
              )}
              {activeTab === 'email_unverified' && (
                <tr>
                  <th>Name</th>
                  <th>Company</th>
                  <th>Email Address</th>
                  <th>Status</th>
                  <th>LinkedIn Profile</th>
                  <th>Logged Date</th>
                </tr>
              )}
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan="10" style={{ textAlign: 'center', padding: '40px 0' }}>
                    <div className="status-spinner" style={{ margin: '0 auto' }}></div>
                    <p style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>Loading logs...</p>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan="10" className="empty-table-cell" style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>
                    No logs found for this category on {activePlatform === 'snov' ? 'Snov.io' : 'Hunter.io'}.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id}>
                    {activeTab === 'linkedin_not_found' && (
                      <>
                        <td>{log.first_name || '-'}</td>
                        <td>{log.last_name || '-'}</td>
                        <td>{log.company_name || '-'}</td>
                        <td>{formatDate(log.created_at)}</td>
                      </>
                    )}
                    {activeTab === 'domain_not_found' && (
                      <>
                        <td>{log.first_name || '-'}</td>
                        <td>{log.last_name || '-'}</td>
                        <td>{log.company_name || '-'}</td>
                        <td>
                          {log.linkedin_url ? (
                            <a href={log.linkedin_url} target="_blank" rel="noopener noreferrer" className="linkedin-link">
                              View Profile
                            </a>
                          ) : '-'}
                        </td>
                        <td>{formatDate(log.created_at)}</td>
                      </>
                    )}
                    {activeTab === 'email_not_found' && (
                      <>
                        <td>{log.first_name || '-'}</td>
                        <td>{log.last_name || '-'}</td>
                        <td>{log.company_name || '-'}</td>
                        <td>{log.domain || '-'}</td>
                        <td>
                          {log.linkedin_url ? (
                            <a href={log.linkedin_url} target="_blank" rel="noopener noreferrer" className="linkedin-link">
                              View Profile
                            </a>
                          ) : '-'}
                        </td>
                        <td>{formatDate(log.created_at)}</td>
                      </>
                    )}
                    {activeTab === 'email_unverified' && (
                      <>
                        <td>{log.first_name} {log.last_name}</td>
                        <td>
                          {log.company_name}
                          {log.domain && <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>{log.domain}</span>}
                        </td>
                        <td className="prospect-no-email-cell" style={{ color: '#f87171' }}>{log.email}</td>
                        <td>
                          <span style={{
                            background: 'rgba(239, 68, 68, 0.1)',
                            color: '#f87171',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            border: '1px solid rgba(239, 68, 68, 0.2)'
                          }}>
                            {log.verification_status || 'unverified'}
                          </span>
                        </td>
                        <td>
                          {log.linkedin_url ? (
                            <a href={log.linkedin_url} target="_blank" rel="noopener noreferrer" className="linkedin-link">
                              View Profile
                            </a>
                          ) : '-'}
                        </td>
                        <td>{formatDate(log.created_at)}</td>
                      </>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {!isLoading && logs.length > 0 && (
            <div className="view-modal-footer" style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '16px', marginTop: '16px' }}>
              <div className="pagination-info" style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                Showing {(page - 1) * limit + 1} to {Math.min(page * limit, totalLogs)} of {totalLogs} entries
              </div>

              <div className="pagination-controls">
                <button
                  className="btn btn-secondary pagination-btn"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </button>
                
                <span className="pagination-info">
                  Page {page} of {totalPages}
                </span>

                <button
                  className="btn btn-secondary pagination-btn"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
