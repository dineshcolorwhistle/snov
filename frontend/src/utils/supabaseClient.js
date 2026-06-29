import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://ocydnvzzvfucjxdjochw.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

// We will export a function to get or initialize the client, 
// allowing it to be configured dynamically if the anon key is supplied in the UI
let supabase = null;

if (supabaseUrl && supabaseAnonKey) {
  supabase = createClient(supabaseUrl, supabaseAnonKey);
}

export const getSupabase = () => {
  if (!supabase) {
    const dynamicAnonKey = localStorage.getItem('supabase_anon_key') || '';
    if (supabaseUrl && dynamicAnonKey) {
      supabase = createClient(supabaseUrl, dynamicAnonKey);
    }
  }
  return supabase;
};

export const initializeSupabase = (anonKey) => {
  localStorage.setItem('supabase_anon_key', anonKey);
  supabase = createClient(supabaseUrl, anonKey);
  return supabase;
};
