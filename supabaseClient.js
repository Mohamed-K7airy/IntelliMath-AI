import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://twkbvvinlzdvtqkauvkv.supabase.co'
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3a2J2dmlubHpkdnRxa2F1dmt2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI0NTI0ODksImV4cCI6MjA4ODAyODQ4OX0.PVUSz03RkXKlMky_qf_U5pAvLU7_CBhB1PaRgTWJ4Zk'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)