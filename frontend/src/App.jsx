import React, { useState, useEffect } from 'react';
import ProspectLists from './components/ProspectLists';
import AddProspectModal from './components/AddProspectModal';
import CreateListModal from './components/CreateListModal';
import ViewProspectsModal from './components/ViewProspectsModal';
import SettingsModal from './components/SettingsModal';
import TrackingLogs from './components/TrackingLogs';
import Login from './components/Login';
import { apiFetch } from './utils/api';
import { getSupabase } from './utils/supabaseClient';

function App() {
  const [lists, setLists] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedList, setSelectedList] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [viewingList, setViewingList] = useState(null);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [toasts, setToasts] = useState([]);
  
  // Navigation: 'dashboard' | 'logs'
  const [activeView, setActiveView] = useState('dashboard');

  // Platform: 'snov' | 'hunter'
  const [platform, setPlatform] = useState(localStorage.getItem('active_platform') || 'snov');
  
  // Authentication states
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Set body theme class on platform change
  useEffect(() => {
    document.body.className = `theme-${platform}`;
    localStorage.setItem('active_platform', platform);
  }, [platform]);

  const addToast = (type, title, message) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      removeToast(id);
    }, 5000);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  const fetchLists = async (silent = false) => {
    if (!user) return;
    if (!silent) setIsLoading(true);
    try {
      const response = await apiFetch(`/api/lists`);
      const data = await response.json();
      
      if (response.ok && data.success) {
        setLists(data.lists);
      } else {
        const errorMsg = data.detail || 'Failed to fetch lead lists.';
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

  // Check auth status on mount and subscribe to changes
  useEffect(() => {
    const checkAuth = async () => {
      const supabase = getSupabase();
      if (!supabase) {
        setAuthLoading(false);
        return;
      }
      
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        const userPayload = {
          email: session.user.email,
          name: session.user.user_metadata?.name || session.user.user_metadata?.full_name || session.user.email.split('@')[0].toUpperCase(),
          id: session.user.id
        };
        setUser(userPayload);
      }
      setAuthLoading(false);
    };

    checkAuth();

    const supabase = getSupabase();
    if (supabase) {
      const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
        if (session) {
          const userPayload = {
            email: session.user.email,
            name: session.user.user_metadata?.name || session.user.user_metadata?.full_name || session.user.email.split('@')[0].toUpperCase(),
            id: session.user.id
          };
          setUser(userPayload);
        } else {
          setUser(null);
        }
      });
      return () => subscription.unsubscribe();
    }
  }, []);

  // Fetch lists when user or platform changes
  useEffect(() => {
    if (user) {
      fetchLists();
    }
  }, [user, platform]);

  // Handle unauthorized event across components
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      addToast('warning', 'Session Expired', 'Your session has expired. Please sign in again.');
    };
    window.addEventListener('auth-unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('auth-unauthorized', handleUnauthorized);
    };
  }, []);

  const handleLoginSuccess = (token, loggedInUser) => {
    setUser(loggedInUser);
    addToast('success', 'Welcome Back', `Logged in successfully as ${loggedInUser.name}.`);
  };

  const handleLogout = async () => {
    const supabase = getSupabase();
    if (supabase) {
      await supabase.auth.signOut();
    }
    setUser(null);
    addToast('success', 'Logged Out', 'You have been logged out.');
  };

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
    addToast('success', 'Lead Added', 'Lead was successfully added to your list.');
    fetchLists(true); // Silent reload to update list totals in the background
  };

  const handleCreateListSuccess = (newList, successMsg) => {
    addToast('success', 'List Created', successMsg || `List '${newList.name}' was successfully created.`);
    setLists((prev) => [newList, ...prev]);
    setIsCreateModalOpen(false);
    setSelectedList(newList);
    setIsModalOpen(true);
  };

  if (authLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <div className="status-spinner"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <Login onLoginSuccess={handleLoginSuccess} />
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

  return (
    <>
      <header className="app-header">
        <div className="logo-container">
          <span className="logo-icon">{platform === 'snov' ? 'S' : 'H'}</span>
          <span className="logo-text">{platform === 'snov' ? 'Snov.io' : 'Hunter.io'}</span>
          <span className="logo-badge">Automation</span>
        </div>

        {/* Platform Selector Switch */}
        <div style={{
          display: 'flex',
          background: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid var(--border-glass)',
          padding: '4px',
          borderRadius: '10px',
          margin: '0 20px'
        }}>
          <button
            onClick={() => setPlatform('snov')}
            style={{
              padding: '6px 16px',
              border: 'none',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              background: platform === 'snov' ? 'var(--primary)' : 'transparent',
              color: platform === 'snov' ? '#000' : 'var(--text-secondary)',
              transition: 'var(--transition-smooth)'
            }}
          >
            Snov.io
          </button>
          <button
            onClick={() => setPlatform('hunter')}
            style={{
              padding: '6px 16px',
              border: 'none',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              background: platform === 'hunter' ? 'var(--primary)' : 'transparent',
              color: platform === 'hunter' ? '#000' : 'var(--text-secondary)',
              transition: 'var(--transition-smooth)'
            }}
          >
            Hunter.io
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Navigation links */}
          <div style={{ display: 'flex', gap: '8px', marginRight: '16px' }}>
            <button
              className={`btn ${activeView === 'dashboard' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveView('dashboard')}
              style={{ padding: '8px 16px', fontSize: '13px' }}
            >
              Dashboard
            </button>
            <button
              className={`btn ${activeView === 'logs' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveView('logs')}
              style={{ padding: '8px 16px', fontSize: '13px' }}
            >
              Tracking Logs
            </button>
          </div>

          <div className="user-profile-badge">
            <span className="user-avatar">{user.name[0].toUpperCase()}</span>
            <span>{user.name}</span>
          </div>

          <button 
            className="btn btn-secondary"
            onClick={() => setIsSettingsOpen(true)}
            style={{ padding: '8px', borderRadius: '10px' }}
            title="API Settings"
          >
            ⚙️
          </button>

          <button 
            className="btn btn-secondary" 
            onClick={handleLogout} 
            style={{ padding: '8px 16px', fontSize: '13px', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171' }}
          >
            Logout
          </button>
        </div>
      </header>

      <main>
        {activeView === 'dashboard' ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '24px' }}>
              <div>
                <h1>{platform === 'snov' ? 'Snov.io' : 'Hunter.io'} Campaigns</h1>
                <p className="section-desc">
                  Retrieve, manage, and enrich lead campaigns directly. Select a list to search, verify business emails, and add leads.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button 
                  className="btn btn-primary" 
                  onClick={() => setIsCreateModalOpen(true)}
                  style={{ padding: '10px 20px', fontSize: '14px' }}
                >
                  <span style={{ fontSize: '16px', fontWeight: 'bold', marginRight: '4px' }}>+</span>
                  Create List
                </button>
                <button 
                  className="btn btn-secondary" 
                  onClick={() => fetchLists()} 
                  disabled={isLoading}
                  style={{ padding: '10px 20px', fontSize: '14px' }}
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
                    style={{ marginRight: '6px', animation: isLoading ? 'spin 1s linear infinite' : 'none' }}
                  >
                    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                  </svg>
                  Refresh
                </button>
              </div>
            </div>

            <ProspectLists 
              lists={lists} 
              isLoading={isLoading} 
              onAddProspectClick={handleAddProspectClick} 
              onViewProspectsClick={handleViewProspectsClick}
              onCreateListClick={() => setIsCreateModalOpen(true)}
            />
          </>
        ) : (
          <>
            <h1>Processing & Verification Logs</h1>
            <p className="section-desc">
              Track unresolved domains, missing LinkedIn profiles, missing emails, and unverified (risky/invalid) emails filtered by the active platform.
            </p>
            <TrackingLogs activePlatform={platform} />
          </>
        )}
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

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSaveSuccess={() => {
          addToast('success', 'Credentials Saved', 'API settings updated successfully. Reloading campaigns...');
          fetchLists();
        }}
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
