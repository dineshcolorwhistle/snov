import React, { useState, useEffect } from 'react';
import ProspectLists from './components/ProspectLists';
import AddProspectModal from './components/AddProspectModal';
import CreateListModal from './components/CreateListModal';
import ViewProspectsModal from './components/ViewProspectsModal';

function App() {
  const [lists, setLists] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedList, setSelectedList] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [viewingList, setViewingList] = useState(null);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [toasts, setToasts] = useState([]);

  const addToast = (type, title, message) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      removeToast(id);
    }, 5000);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  const fetchLists = async (silent = false) => {
    if (!silent) setIsLoading(true);
    try {
      const response = await fetch('/api/lists');
      const data = await response.json();
      
      if (response.ok && data.success) {
        setLists(data.lists);
      } else {
        const errorMsg = data.detail || 'Failed to fetch prospect lists.';
        addToast('error', 'Error Fetching Lists', errorMsg);
        setLists([]);
      }
    } catch (err) {
      console.error(err);
      addToast(
        'error', 
        'Connection Error', 
        'Unable to connect to the backend server. Please verify the Python server is running on port 8000.'
      );
      setLists([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLists();
  }, []);

  const handleAddProspectClick = (list) => {
    setSelectedList(list);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedList(null);
  };

  const handleViewProspectsClick = (list) => {
    setViewingList(list);
    setIsViewModalOpen(true);
  };

  const handleViewModalClose = () => {
    setIsViewModalOpen(false);
    setViewingList(null);
  };

  const handleProspectAdded = () => {
    addToast('success', 'Prospect Added', 'Prospect was successfully added to Snov.io.');
    fetchLists(true); // Silent reload to update list totals in the background
  };

  const handleCreateListSuccess = (newList, successMsg) => {
    addToast('success', 'List Created', successMsg || `List '${newList.name}' was successfully created.`);
    
    // Optimistically prepend to existing lists
    setLists((prev) => [newList, ...prev]);
    
    // Close creation modal and immediately open add prospect modal for this new list
    setIsCreateModalOpen(false);
    setSelectedList(newList);
    setIsModalOpen(true);
  };

  return (
    <>
      <header className="app-header">
        <div className="logo-container">
          <span className="logo-icon">S</span>
          <span className="logo-text">Snov.io</span>
          <span className="logo-badge">Automation</span>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            className="btn btn-primary" 
            onClick={() => setIsCreateModalOpen(true)}
            style={{ padding: '8px 16px', fontSize: '13px' }}
          >
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>+</span>
            Create List
          </button>
          <button 
            className="btn btn-secondary" 
            onClick={() => fetchLists()} 
            disabled={isLoading}
            style={{ padding: '8px 16px', fontSize: '13px' }}
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
              style={{ marginRight: '4px', animation: isLoading ? 'spin 1s linear infinite' : 'none' }}
            >
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Refresh Lists
          </button>
        </div>
      </header>

      <main>
        <h1>Prospect Lists</h1>
        <p className="section-desc">
          Retrieve, manage, and enrich lead campaigns directly from your Snov.io account. Select a list to search for business emails and add prospects.
        </p>

        <ProspectLists 
          lists={lists} 
          isLoading={isLoading} 
          onAddProspectClick={handleAddProspectClick} 
          onViewProspectsClick={handleViewProspectsClick}
          onCreateListClick={() => setIsCreateModalOpen(true)}
        />
      </main>

      <AddProspectModal 
        list={selectedList}
        isOpen={isModalOpen}
        onClose={handleModalClose}
        onSuccess={handleProspectAdded}
      />

      <CreateListModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleCreateListSuccess}
        lists={lists}
      />

      <ViewProspectsModal
        list={viewingList}
        isOpen={isViewModalOpen}
        onClose={handleViewModalClose}
      />

      {/* Toast Alert notifications stack */}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            <span className={`toast-icon toast-icon-${toast.type}`}>
              {toast.type === 'success' && '✓'}
              {toast.type === 'error' && '✕'}
              {toast.type === 'warning' && '⚠'}
            </span>
            <div className="toast-content">
              <div className="toast-title">{toast.title}</div>
              <div className="toast-message">{toast.message}</div>
            </div>
            <button className="toast-close" onClick={() => removeToast(toast.id)}>
              &times;
            </button>
          </div>
        ))}
      </div>
    </>
  );
}

export default App;
