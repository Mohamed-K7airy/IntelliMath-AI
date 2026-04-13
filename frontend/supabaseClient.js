// ✅ FIX (W-03): Import from node_modules instead of CDN to avoid double-loading and version mismatch
import { createClient } from '@supabase/supabase-js';

// Handle environment variables safely across different serve methods.
// IMPORTANT: Do not hardcode Supabase credentials in-repo. Configure via env vars.
let supabaseUrl = '';
let supabaseAnonKey = '';

if (typeof import.meta !== 'undefined' && import.meta.env) {
    // Vite environment
    supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
    supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
}

if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
        'Missing Supabase env vars. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY (see .env.example).'
    );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)