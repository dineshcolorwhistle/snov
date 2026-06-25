import React, { useState, useEffect } from 'react';

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  try {
    // Snov date format: "2026-06-23 07:54:00.000000"
    const cleanStr = dateStr.split('.')[0].replace(/-/g, '/');
    const date = new Date(cleanStr + ' UTC');
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  } catch (e) {
    return dateStr.split(' ')[0] || dateStr;
  }
};

const SkeletonRow = () => (
  <tr className="skeleton-row">
    <td><div className="skeleton-cell" style={{ width: '80px' }}></div></td>
    <td><div className="skeleton-cell" style={{ width: '80px' }}></div></td>
    <td><div className="skeleton-cell" style={{ width: '120px' }}></div></td>
    <td><div className="skeleton-cell" style={{ width: '140px' }}></div></td>
    <td><div className="skeleton-cell" style={{ width: '160px' }}></div></td>
    <td><div className="skeleton-cell" style={{ width: '100px' }}></div></td>
  </tr>
);

export default function ViewProspectsModal({ list, isOpen, onClose }) {
  const [prospects, setProspects] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Pagination state
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10); // Default to 10 prospects per page for better UI fit
  const [totalContacts, setTotalContacts] = useState(0);
  const [creationDate, setCreationDate] = useState('');

  const fetchProspects = async () => {
    if (!list) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/lists/${list.id}/prospects?page=${page}&limit=${limit}`);
      const data = await response.json();

      if (response.ok && data.success) {
        setProspects(data.prospects || []);
        
        // Update total contacts and creation date from API response if present
        if (data.list) {
          if (data.list.contacts !== undefined) {
            setTotalContacts(data.list.contacts);
          }
          if (data.list.creationDate && data.list.creationDate.date) {
            setCreationDate(data.list.creationDate.date);
          }
        }
      } else {
        const errorMsg = data.detail || 'Failed to retrieve prospects for this list.';
        setError(errorMsg);
      }
    } catch (err) {
      console.error(err);
      setError('Unable to connect to the backend server. Please verify the Python server is running.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && list) {
      fetchProspects();
    } else {
      // Reset state when closed
      setProspects([]);
      setPage(1);
      setError(null);
      setTotalContacts(list ? list.contacts : 0);
      setCreationDate('');
    }
  }, [isOpen, list, page, limit]);

  if (!isOpen) return null;

  const totalPages = Math.max(1, Math.ceil(totalContacts / limit));
  const displayCreationDate = creationDate || (list && list.creationDate ? list.creationDate.date : '');

  return (
    <div className="modal-overlay" onClick={onClose} id="view-prospects-overlay">
      <div 
        className="modal-content view-prospects-modal" 
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '1000px', width: '95%' }}
      >
        <button 
          className="modal-close" 
          onClick={onClose} 
          aria-label="Close modal"
          id="close-view-prospects"
        >
          &times;
        </button>

        <div className="view-modal-header">
          <h2 className="modal-title" style={{ fontSize: '24px' }}>
            {list ? list.name : 'Prospect List'}
          </h2>
          <div className="view-modal-meta">
            <span className="meta-stat">
              <strong>{totalContacts}</strong> prospect{totalContacts !== 1 ? 's' : ''}
            </span>
            {displayCreationDate && (
              <span className="meta-divider">•</span>
            )}
            {displayCreationDate && (
              <span className="meta-date">
                Created: {formatDate(displayCreationDate)}
              </span>
            )}
          </div>
        </div>

        <div className="view-modal-body">
          {error ? (
            <div className="modal-status-screen">
              <div className="status-icon-error">✕</div>
              <div className="status-title">Error Loading Prospects</div>
              <div className="status-desc">{error}</div>
              <button 
                className="btn btn-secondary" 
                onClick={fetchProspects}
                id="btn-retry-fetch-prospects"
              >
                Retry Loading
              </button>
            </div>
          ) : (
            <div className="prospects-table-container">
              <table className="prospects-table">
                <thead>
                  <tr>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Company Name</th>
                    <th>Company Domain</th>
                    <th>Email Address</th>
                    <th>LinkedIn Profile</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <>
                      <SkeletonRow />
                      <SkeletonRow />
                      <SkeletonRow />
                      <SkeletonRow />
                      <SkeletonRow />
                    </>
                  ) : prospects.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="empty-table-cell">
                        No prospects found in this list.
                      </td>
                    </tr>
                  ) : (
                    prospects.map((prospect) => {
                      const email = prospect.emails && prospect.emails.length > 0 
                        ? prospect.emails[0].email 
                        : null;
                        
                      return (
                        <tr key={prospect.id}>
                          <td>{prospect.firstName || '-'}</td>
                          <td>{prospect.lastName || '-'}</td>
                          <td>{prospect.companyName || '-'}</td>
                          <td>{prospect.companySite || '-'}</td>
                          <td className={email ? 'prospect-email-cell' : 'prospect-no-email-cell'}>
                            {email ? email : '-'}
                          </td>
                          <td>
                            {prospect.linkedinUrl ? (
                              <a 
                                href={prospect.linkedinUrl.replace(/&amp;/g, '&')} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="linkedin-link"
                                style={{ color: 'var(--primary)', textDecoration: 'underline' }}
                              >
                                View Profile
                              </a>
                            ) : '-'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {!error && !isLoading && prospects.length > 0 && (
          <div className="view-modal-footer">
            <div className="limit-selector-container">
              <span className="limit-label">Show:</span>
              <select 
                value={limit} 
                onChange={(e) => {
                  setLimit(Number(e.target.value));
                  setPage(1); // Reset to first page when changing page size
                }}
                className="limit-select"
                id="select-limit"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div className="pagination-controls">
              <button
                className="btn btn-secondary pagination-btn"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                id="btn-prev-page"
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
                id="btn-next-page"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
