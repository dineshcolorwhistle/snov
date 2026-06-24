import React, { useState, useEffect } from 'react';

export default function CreateListModal({ isOpen, onClose, onSuccess, lists }) {
  const [listName, setListName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setListName('');
      setError('');
      setIsLoading(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const validate = () => {
    const trimmed = listName.trim();
    if (!trimmed) {
      setError('List name is required');
      return false;
    }
    
    // Check if list already exists in existing lists (case-insensitive)
    const exists = lists.some(
      (list) => list.name.toLowerCase() === trimmed.toLowerCase()
    );
    if (exists) {
      setError(`A prospect list named '${trimmed}' already exists`);
      return false;
    }

    setError('');
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/lists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: listName.trim() }),
      });
      const data = await response.json();

      if (response.ok && data.success) {
        onSuccess(data.list, data.message || 'List created successfully!');
      } else {
        setError(data.detail || 'Failed to create list.');
      }
    } catch (err) {
      console.error(err);
      setError('Could not connect to the backend server. Make sure the backend server is running on port 8000.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={isLoading ? undefined : onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {!isLoading && (
          <button className="modal-close" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        )}

        {!isLoading ? (
          <>
            <h2 className="modal-title">Create New List</h2>
            <p className="modal-subtitle">
              Enter a name for the new prospect list.
            </p>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label" htmlFor="list-name">List Name</label>
                <input
                  id="list-name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. email-not-found-cw1"
                  value={listName}
                  onChange={(e) => {
                    setListName(e.target.value);
                    if (error) setError('');
                  }}
                  autoFocus
                />
                {error && <span className="form-error-msg">{error}</span>}
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={onClose}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create List
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="modal-status-screen">
            <div className="status-spinner" />
            <h3 className="status-title">Creating List</h3>
            <p className="status-desc">
              Registering new prospect list with Snov.io API...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
