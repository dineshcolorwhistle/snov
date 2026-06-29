import { getSupabase } from './supabaseClient';

export const getAuthToken = async () => {
  const supabase = getSupabase();
  if (!supabase) return null;
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || null;
};

export const apiFetch = async (url, options = {}) => {
  const token = await getAuthToken();
  const activePlatform = localStorage.getItem('active_platform') || 'snov';
  
  // Automatically append platform to the URL if not already present
  const separator = url.includes('?') ? '&' : '?';
  const finalUrl = url.includes('platform=') ? url : `${url}${separator}platform=${activePlatform}`;
  
  const headers = {
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  headers['X-Platform'] = activePlatform;
  
  const response = await fetch(finalUrl, {
    ...options,
    headers,
  });
  
  if (response.status === 401) {
    // Dispatch a custom event to notify App.jsx of unauthorization
    window.dispatchEvent(new Event('auth-unauthorized'));
  }
  
  return response;
};
