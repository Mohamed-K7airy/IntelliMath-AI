import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm'

// Handle environment variables safely across different serve methods
let supabaseUrl = '';
let supabaseAnonKey = '';

if (typeof import.meta !== 'undefined' && import.meta.env) {
    // Vite environment
    supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
    supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
}

if (!supabaseUrl || !supabaseAnonKey) {
    console.warn('Supabase configuration missing! Using project fallbacks...');
    supabaseUrl = supabaseUrl || 'https://twkbvvinlzdvtqkauvkv.supabase.co';
    supabaseAnonKey = supabaseAnonKey || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3a2J2dmlubHpkdnRxa2F1dmt2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI0NTI0ODksImV4cCI6MjA4ODAyODQ4OX0.PVUSz03RkXKlMky_qf_U5pAvLU7_CBhB1PaRgTWJ4Zk';
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)