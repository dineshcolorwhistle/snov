import React from 'react';

const SkeletonCard = () => (
  <div className="skeleton-card">
    <div className="list-info">
      <div className="skeleton-text" />
      <div className="skeleton-text mid" />
    </div>
    <div className="skeleton-btn" />
  </div>
);

export default function ProspectLists({ lists, isLoading, onAddProspectClick }) {
  if (isLoading) {
    return (
      <div className="lists-grid">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (!lists || lists.length === 0) {
    return (
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-glass)',
        padding: '40px',
        borderRadius: '16px',
        textAlign: 'center',
        color: 'var(--text-secondary)'
      }}>
        <h3 style={{ color: 'var(--text-primary)', marginBottom: '8px', fontSize: '18px' }}>
          No prospect lists found
        </h3>
        <p style={{ fontSize: '14px' }}>
          Make sure your Snov.io account has active prospect lists and that your API Client ID and Secret are configured correctly in the backend `.env` file.
        </p>
      </div>
    );
  }

  return (
    <div className="lists-grid">
      {lists.map((list) => (
        <div key={list.id} className="list-card">
          <div className="list-info">
            <h3>{list.name}</h3>
            <div className="list-stats">
              <span className="list-stats-count">{list.contacts}</span>
              <span>prospect{list.contacts !== 1 ? 's' : ''}</span>
            </div>
          </div>
          <button 
            className="btn btn-primary btn-add-prospect"
            onClick={() => onAddProspectClick(list)}
          >
            <svg 
              width="16" 
              height="16" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2.5" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            >
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            Add Prospect
          </button>
        </div>
      ))}
    </div>
  );
}
