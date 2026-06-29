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

export default function ProspectLists({ lists, isLoading, onAddProspectClick, onViewProspectsClick, onCreateListClick }) {
  const activePlatform = localStorage.getItem('active_platform') || 'snov';
  const platformName = activePlatform === 'snov' ? 'Snov.io' : 'Hunter.io';

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
        <p style={{ fontSize: '14px', marginBottom: '20px' }}>
          Make sure your {platformName} account has active lists and that your API credentials are configured correctly in the Settings modal.
        </p>
        <button className="btn btn-primary" onClick={onCreateListClick}>
          <span style={{ fontSize: '18px', marginRight: '4px', lineHeight: 1 }}>+</span>
          Create New List
        </button>
      </div>
    );
  }

  return (
    <div className="lists-grid">
      <div className="list-card create-list-card" onClick={onCreateListClick}>
        <div className="create-list-icon">+</div>
        <div className="create-list-title">Create New List</div>
      </div>

      {lists.map((list) => (
        <div key={list.id} className="list-card">
          <div className="list-info">
            <h3>{list.name}</h3>
            <div className="list-stats">
              <span className="list-stats-count">{list.contacts}</span>
              <span>prospect{list.contacts !== 1 ? 's' : ''}</span>
            </div>
          </div>
          <div className="list-actions">
            <button 
              className="btn btn-secondary btn-view-prospects"
              onClick={() => onViewProspectsClick(list)}
              id={`btn-view-${list.id}`}
            >
              <svg 
                width="14" 
                height="14" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2.5" 
                strokeLinecap="round" 
                strokeLinejoin="round"
              >
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              View
            </button>
            <button 
              className="btn btn-primary btn-add-prospect"
              onClick={() => onAddProspectClick(list)}
              id={`btn-add-${list.id}`}
            >
              <svg 
                width="14" 
                height="14" 
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
        </div>
      ))}
    </div>
  );
}
