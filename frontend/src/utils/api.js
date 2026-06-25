export const getAuthToken = () => localStorage.getItem('token');

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
};

export const apiFetch = async (url, options = {}) => {
  const token = getAuthToken();
  
  // Set headers correctly depending on whether body is FormData or JSON
  const headers = {
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  if (response.status === 401) {
    // Clear token as session is invalid or expired
    localStorage.removeItem('token');
    // Dispatch a custom event to notify App.jsx of unauthorization
    window.dispatchEvent(new Event('auth-unauthorized'));
  }
  
  return response;
};
